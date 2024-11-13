import requests
from flask import Flask, request, jsonify, render_template
from collections import defaultdict
import time
import logging
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    user_id = request.json.get('user_id', '123123***')  # Default user_id if not provided
    print(f"Received request: message='{user_input}', user_id='{user_id}'")
    return chat_and_format_response(user_input, user_id)

def chat_and_format_response(user_input, user_id='123123***'):
    conversation_id = retrieve_conversation_id(user_id)
    if not conversation_id:
        conversation_id = create_conversation(user_id)
        if not conversation_id:
            print("Failed to create conversation")
            return jsonify({"error": "Failed to create conversation"}), 400

    chat_id = chat_with_bot(user_input, user_id, conversation_id)
    print(f"chat_with_bot response (chat_id): {chat_id}")
    
    if chat_id:
        messages = retrieve_chat_messages(chat_id, conversation_id)
        print(f"Retrieved messages: {messages}")
        
        # 只提取“answer”类型的消息
        answer_messages = [msg for msg in messages if msg.get('type') == 'answer']
        if answer_messages:
            bot_response = answer_messages[0].get('content', 'No response from bot.')
            print(f"Bot response: {bot_response}")
            return jsonify({"message": bot_response})
        else:
            print("No valid messages found")
            return jsonify({"error": "No valid messages found"}), 400
    else:
        error_response = {"error": "Failed to chat with bot"}
        print(f"Error response to client: {error_response}")
        return jsonify(error_response), 400


# 在文件顶部添加这个导入
user_conversations = defaultdict(str)

def retrieve_conversation_id(user_id):
    """Retrieve the conversation_id for the user."""
    return user_conversations.get(user_id)

def save_conversation_id(user_id, conversation_id):
    """Save the conversation_id for the user."""
    user_conversations[user_id] = conversation_id

def create_conversation(user_id):
    """Create a new conversation and return the conversation_id."""
    api_url = 'https://api.coze.cn/v3/chat'
    headers = {
        'Authorization': 'Bearer pat_DTaabzJCMdTFJOzEdPkdmoMGAGkDvOzwfuhVOs4ZIgFMfyv6DiF31Y1MhZ3mOqLO',
        'Content-Type': 'application/json'
    }
    data = {
        "bot_id": "7436172217597837362",  #在这里填写你的bot_id
        "user_id": user_id, 
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": "Start a new conversation",
                "content_type": "text"
            }
        ]
    }

    print(f"Creating conversation for user: {user_id}")
    response = requests.post(api_url, headers=headers, json=data)
    print(f"Create Conversation API Response status: {response.status_code}")
    print(f"Create Conversation API Response content: {response.text}")
    
    if response.status_code == 200:
        conversation_id = response.json().get('data', {}).get('conversation_id')
        if conversation_id:
            save_conversation_id(user_id, conversation_id)
        return conversation_id
    else:
        print("Failed to create conversation.")
        return None

def chat_with_bot(user_input, user_id='123123***', conversation_id=None):
    """Handle chat with bot, using the provided conversation_id."""
    if not conversation_id:
        conversation_id = retrieve_conversation_id(user_id)
    
    if not conversation_id:
        conversation_id = create_conversation(user_id)
    
    if not conversation_id:
        print("Failed to create or retrieve conversation_id")
        return None

    # Proceed with sending the user input to the bot
    api_url = f'https://api.coze.cn/v3/chat?conversation_id={conversation_id}'
    headers = {
        'Authorization': 'Bearer pat_DTaab', #这里填你的鉴权token
        'Content-Type': 'application/json'
    }
    data = {
        "bot_id": "7436172217597837362",  #在这里填写你的bot_id
        "user_id": user_id,
        "stream": False,
        "auto_save_history": True,
        "additional_messages": [
            {
                "role": "user",
                "content": user_input,
                "content_type": "text"
            }
        ]
    }

    print(f"Sending request to Coze API: {data}")
    try:
        response = requests.post(api_url, headers=headers, json=data)
        print(f"Coze API Response status: {response.status_code}")
        print(f"Coze API Response content: {response.text}")
        
        response.raise_for_status()  # This will raise an exception for HTTP errors
        
        response_json = response.json()
        chat_id = response_json.get('data', {}).get('id')
        if chat_id:
            return chat_id
        else:
            print("No chat_id found in response")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error occurred while sending request to Coze API: {e}")
        return None
    except ValueError as e:
        print(f"Error decoding JSON response: {e}")
        return None

def retrieve_chat_messages(chat_id, conversation_id, max_retries=6, delay=4):
    """Retrieve messages from the chat using chat_id and conversation_id with retries."""
    api_url = f'https://api.coze.cn/v3/chat/message/list?chat_id={chat_id}&conversation_id={conversation_id}'
    headers = {
        'Authorization': 'Bearer pat_DTaabzJCMdTFJOzEdPkdmoMGAGkDvOzwfuhVOs4ZIgFMfyv6DiF31Y1MhZ3mOqLO',
        'Content-Type': 'application/json'
    }

    for attempt in range(max_retries):
        print(f"Retrieving messages for chat_id: {chat_id}, conversation_id: {conversation_id} (Attempt {attempt + 1})")
        try:
            response = requests.get(api_url, headers=headers)
            print(f"Retrieve Messages API Response status: {response.status_code}")
            print(f"Retrieve Messages API Response content: {response.text}")
            
            response.raise_for_status()
            
            response_json = response.json()
            messages = response_json.get('data', [])
            if messages:
                # Filter messages to find the one with type "answer"
                answer_messages = [msg for msg in messages if msg.get('type') == 'answer']
                if answer_messages:
                    return answer_messages  # Return only the answer messages
                else:
                    print(f"No answer messages found in response (Attempt {attempt + 1})")
            else:
                print(f"No messages found in response (Attempt {attempt + 1})")
                
            if attempt < max_retries - 1:
                print(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        except requests.exceptions.RequestException as e:
            print(f"Error occurred while retrieving messages: {e}")
            if attempt < max_retries - 1:
                print(f"Waiting {delay} seconds before retrying...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
        except ValueError as e:
            print(f"Error decoding JSON response: {e}")
            return []
    
    print("Max retries reached. Unable to retrieve messages.")
    return []

def chat_and_format_response(user_input, user_id='123123***'):
    conversation_id = retrieve_conversation_id(user_id)
    if not conversation_id:
        conversation_id = create_conversation(user_id)
        if not conversation_id:
            print("Failed to create conversation")
            return jsonify({"error": "Failed to create conversation"}), 400

    chat_id = chat_with_bot(user_input, user_id, conversation_id)
    print(f"chat_with_bot response (chat_id): {chat_id}")
    
    if chat_id:
        messages = retrieve_chat_messages(chat_id, conversation_id)
        print(f"Retrieved messages: {messages}")
        
        if messages and isinstance(messages, list) and len(messages) > 0:
            for message in reversed(messages):
                if message.get('type') == 'answer':
                    bot_response = message.get('content', 'No response from bot.')
                    break
                elif message.get('type') == 'verbose':
                    try:
                        content = json.loads(message.get('content', '{}'))
                        bot_response = content.get('msg_type', 'Verbose message received.')
                    except json.JSONDecodeError:
                        bot_response = 'Unable to parse verbose message.'
                    break
                elif message.get('type') == 'knowledge_recall':
                    try:
                        content = json.loads(message.get('content', '{}'))
                        # 提取knowledge_recall中的数据
                        data_content = content.get('data', 'No data found in knowledge recall.')
                        bot_response = data_content  # 或者根据需要进一步处理
                    except json.JSONDecodeError:
                        bot_response = 'Unable to parse knowledge recall message.'
                    break
            else:
                bot_response = 'No valid response from bot.'
            
            
            print(f"Bot response: {bot_response}")
            return jsonify({"message": bot_response})
        else:
            print("No valid messages found")
            return jsonify({"error": "No valid messages found"}), 400
    else:
        error_response = {"error": "Failed to chat with bot"}
        print(f"Error response to client: {error_response}")
        return jsonify(error_response), 400



if __name__ == '__main__':
     app.run(port=5000)

