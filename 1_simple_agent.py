from openai import OpenAI
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

client = OpenAI(
    api_key=OPENAI_API_KEY
)

def translate_text(text, source_lang="English", target_lang="French"):
    """
    Translates a given text from one language to another using OpenAI's GPT-4 API.

    Args:
        text (str): The text to translate.
        source_lang (str): The source language of the text.
        target_lang (str): The target language for the translation.

    Returns:
        str: The translated text provided by GPT-4.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": f"You are a translator that translates {source_lang} to {target_lang}."},
                {"role": "user", "content": f"Translate the following text: '{text}'"}
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    text_to_translate = "This is a test sentence to translate into French."
    translation = translate_text(text_to_translate)

    print("Translation:", translation)