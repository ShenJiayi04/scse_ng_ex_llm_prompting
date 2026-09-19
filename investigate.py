## Import the necessary modules
import json
import sys
from ollama import chat

## Import the function from the module parse_data
from parse_data import load_items, get_unclaimed_items, save_result

## Build your prompt based on the description the user provides 
## and the items that are available in the lost-and-found database.
## The model must follow the rules listed in the README file
## The function should return the system prompt and the user prompt.
## You may need to use json.dumps() to convert the available_items list into a JSON string.

def build_prompt(description, available_items):
    system_prompt = (
        "You are a campus lost-and-found assistant. "
        "Your job is to match a user's description of a lost item "
        "against a list of available found items.\n\n"
        "Rules for the Model:\n"
        "- The model must use only the given JSON file\n"
        "- Not all the details of an item must match to be a possible match.\n"
        "- Only JSON must be returned, with exactly the following strucutre:\n"
        '{\n    "matches": ["ITEM_ID"],\n    "confidence": "LOW"\n}\n'
        "- 'matches' contains all the possible matches\n"
        "- 'confidence' measures how confident the model is about the matches. \n"
        "It must be exactly one of: LOW, MEDIUM, HIGH.\n"
        "- If there is no match the the model must return the an empty list\n"
    )

    items_json = json.dumps(available_items, indent=4)

    user_prompt = (
        f"User description of the lost item:\n{description}\n\n"
        f"Available found items (JSON):\n{items_json}\n\n"
        "Return the JSON result now."
    )

    return system_prompt, user_prompt
    pass
    

## Logic to ask Qwen for all the possible matches based on the system prompt and user prompt.
## The function should return the response from Qwen.
def ask_qwen(system_prompt, user_prompt):
    response = chat(
        model="qwen3:8b",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response["message"]["content"]
    pass


## Logic to parse the response from Qwen and return the result. 
## You may need to use json.loads() to convert the response string into a suitable Python data structure.
def parse_response(response_text):
    text = response_text.strip()

    
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]

    return json.loads(text)
    pass
    


## Logic to validate the result returned by Qwen.
## It should check if the result is a dictionary, contains the keys "matches" and "confidence", and that the values are of the correct type.
## If everything is correct, then it should check if the item IDs in the "matches" list are valid IDs .
def validate_result(result, available_items):
    if not isinstance(result, dict):
        return False

    if "matches" not in result or "confidence" not in result:
        return False

    if not isinstance(result["matches"], list):
        return False

    if result["confidence"] not in ("LOW", "MEDIUM", "HIGH"):
        return False

    valid_ids = {item["id"] for item in available_items}
    for item_id in result["matches"]:
        if not isinstance(item_id, str) or item_id not in valid_ids:
            return False

    return True
    pass


## Logic to display the matches found by Qwen in a user-friendly format.
## It should look something like this:
""" 
CAMPUS LOST-AND-FOUND ASSISTANT
==================================================

Describe the item you lost: I lost a black bag somewhere

Searching for possible matches...

MATCH RESULT
--------------------------------------------------
Confidence: MEDIUM

Possible matches:

ID: F101
Item: backpack
Color: black
Location: Library 2nd floor
Date found: 2026-09-15

Result saved to output/match_result.json
 """
## If no matches are found, it should display a message indicating that no matches were found, along with the empty list
def display_matches(result, available_items):
    print("\nMATCH RESULT")
    print("-" * 50)
    print(f"Confidence: {result['confidence']}\n")

    if not result["matches"]:
        print("No matches were found.")
        print("Possible matches: []")
        return

    print("Possible matches:\n")
    items_by_id = {item["id"]: item for item in available_items}

    for item_id in result["matches"]:
        item = items_by_id.get(item_id)
        if item:
            print(f"ID: {item['id']}")
            print(f"Item: {item['item']}")
            print(f"Color: {item['color']}")
            print(f"Location: {item['location']}")
            print(f"Date found: {item['date']}")
            print()
    pass
    

## Control center for the entire program.
def main():
    items_filename = "found_items.json"
    output_filename = "output/match_result.json"

    print("CAMPUS LOST-AND-FOUND ASSISTANT")
    print("=" * 50)

    description = input("\nDescribe the item you lost: ")

    print("\nSearching for possible matches...")

    all_items = load_items(items_filename)
    unclaimed_items = get_unclaimed_items(all_items)

    system_prompt, user_prompt = build_prompt(description, unclaimed_items)

    try:
        response_text = ask_qwen(system_prompt, user_prompt)
    except Exception as e:
        print(f"\nError contacting Qwen via Ollama: {e}")
        print("Make sure Ollama is running and 'qwen3:8b' is installed.")
        sys.exit(1)

    try:
        result = parse_response(response_text)
    except json.JSONDecodeError as e:
        print(f"\nFailed to parse model response as JSON: {e}")
        print("Raw response:\n", response_text)
        sys.exit(1)

    if not validate_result(result, unclaimed_items):
        print("\nInvalid result returned by the model.")
        print("Result:", result)
        sys.exit(1)

    display_matches(result, unclaimed_items)

    save_result(result, output_filename)
    print(f"Result saved to {output_filename}")
    pass


if __name__ == "__main__":
    main()