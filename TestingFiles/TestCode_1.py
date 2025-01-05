import openai

# Set your API key
openai.api_key = "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"

# Choose model
model_name = "gpt-4-turbo"  # or 'gpt-3.5-turbo'

def chat_with_gpt(prompt):
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response['choices'][0]['message']['content']

# Test the chatbot
while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break
    response = chat_with_gpt(user_input)
    print(f"AI: {response}")