import os
import requests
from dotenv import load_dotenv

def get_chat_id():
    load_dotenv()
    bot_token = os.environ.get("NGO_PROJECT_TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("Error: NGO_PROJECT_TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        print("Checking for messages to your bot @ngoprojects_bot...")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if data.get("ok"):
            results = data.get("result", [])
            if not results:
                print("\n📭 No messages found yet.")
                print("👉 ACTION REQUIRED: Open Telegram, search for @ngoprojects_bot, click 'Start' (or send a 'hello' message).")
                print("Then run this script again: python get_chat_id.py")
            else:
                latest = results[-1]
                if "message" in latest:
                    chat_id = latest["message"]["chat"]["id"]
                    first_name = latest["message"]["chat"].get("first_name", "User")
                    print(f"\n✅ Success! Found a message from {first_name}.")
                    print(f"Your Chat ID is: {chat_id}")
                    print(f"\nUpdating your .env file automatically...")
                    
                    with open(".env", "a") as f:
                        f.write(f"\nNGO_PROJECT_TELEGRAM_CHAT_ID={chat_id}\n")
                    print("✅ .env file updated successfully! You can now run: python main.py")
                else:
                    print("\nFound updates but no direct messages. Try sending a normal text message to @ngoprojects_bot.")
        else:
            print(f"\nError from Telegram API: {data.get('description')}")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to Telegram API: {e}")

if __name__ == "__main__":
    get_chat_id()
