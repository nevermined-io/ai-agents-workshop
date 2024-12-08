import tempfile
from pathlib import Path
from openai import OpenAI

class OpenAITools:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def text2speech(self, input_text: str) -> str:
        response = self.client.audio.speech.create(
            model='tts-1',
            voice='alloy',
            input=input_text,
        )
        tmp_dir = tempfile.mkdtemp(prefix='text2speech-temp-')
        speech_file = Path(tmp_dir) / 'text2speech.mp3'
        response.write_to_file(speech_file)
        
        return str(speech_file)
    
    def translate_text(self, text: str, source_lang: str = "Spanish", target_lang: str = "English") -> str:
        """
        Translates a given text from one language to another using OpenAI's GPT-4 API.

        Args:
            text (str): The text to translate.
            source_lang (str): The source language of the text (default: "English").
            target_lang (str): The target language for the translation (default: "French").

        Returns:
            str: The translated text.

        Raises:
            Exception: Returns an error message if the API call fails.
        """
        try:
            # Make a request to the OpenAI API for translation
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a translator that translates {source_lang} to {target_lang}."},
                    {"role": "user", "content": f"Translate the following text: '{text}'. Do not generate any additional text beyond the translation."}
                ],
            )
            return response.choices[0].message.content  # Extract and return the translation
        except Exception as e:
            return f"Error: {str(e)}"