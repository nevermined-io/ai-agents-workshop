"""
Translator Agent

This module provides a TranslatorAgent class that interacts with OpenAI's GPT-4 API
to translate text, ntegrating Nevermined payment system and AI protocol.

Classes:
    TranslatorAgent: Handles translation and task execution.
    
Functions:
    main(): Initializes the payment system and the translator agent, then starts the subscription task.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
from payments_py import Payments, Environment
from payments_py.data_models import AgentExecutionStatus, TaskLog

# Load environment variables from the .env file
load_dotenv()

# Constants for API keys and environment setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT")
NVM_API_KEY = os.environ.get("NVM_API_KEY")
AGENT_DID = os.environ.get("AGENT_DID")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)


class TranslatorAgent:
    """
    A class to handle text translation tasks using OpenAI's GPT-4 API.

    Attributes:
        payment (Payments): Instance of the Payments class for task handling and logging.
    """

    def __init__(self, payment):
        """
        Initializes the TranslatorAgent with the provided payment instance.

        Args:
            payment (Payments): The payment system integration for task and logging management.
        """
        self.payment = payment

    async def run(self, data):
        """
        Main entry point for the agent to handle incoming tasks.
        """
        step = self.payment.ai_protocol.get_step(data["step_id"])

        if not self._is_step_pending(step):
            return

        await self._log_task_start(data["task_id"])

        try:
            translated_text = self._translate_text(step["input_query"])
            self._update_step(data, translated_text)
            await self._log_task_completion(data["task_id"])
        except Exception as e:
            await self._log_task_error(data["task_id"], str(e))

    def _is_step_pending(self, step):
        """
        Validates if the step is in a pending state.
        """
        if step['step_status'] != AgentExecutionStatus.Pending.value:
            print("Step is not pending")
            return False
        return True

    async def _log_task_start(self, task_id):
        """
        Logs the start of a task.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message="Starting translation",
            level="info",
        ))

    def _translate_text(self, input_text, source_lang="Spanish", target_lang="English"):
        """
        Translates the input text using OpenAI's GPT-4 API.
        """
        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": f"You are a translator that translates {source_lang} to {target_lang}."},
                    {"role": "user", "content": f"Translate the following text: '{input_text}'. Do not generate any additional text beyond the translation."}
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"Error during translation: {str(e)}")

    def _update_step(self, data, translated_text):
        """
        Updates the step status and adds the translation result.
        """
        self.payment.ai_protocol.update_step(
            did=data["did"],
            task_id=data["task_id"],
            step_id=data["step_id"],
            step={
                "step_id": data["step_id"],
                "task_id": data["task_id"],
                "step_status": AgentExecutionStatus.Completed.value,
                "output": translated_text,
                "output_artifacts": [],
                "is_last": True
            }
        )

    async def _log_task_completion(self, task_id):
        """
        Logs the successful completion of a task.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message="Translation complete",
            level="info",
            task_status=AgentExecutionStatus.Completed.value
        ))

    async def _log_task_error(self, task_id, error_message):
        """
        Logs an error encountered during task execution.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message=f"Error translating text: {error_message}",
            level="error",
            task_status=AgentExecutionStatus.Failed.value
        ))


async def main():
    """
    Main function to initialize the TranslatorAgent and handle subscription tasks.

    This function:
        - Initializes the payment system.
        - Creates a TranslatorAgent instance.
        - Starts the subscription task for the agent.
    """
    # Initialize the payment system
    payment = Payments(
        app_id="my_first_agent",
        version="1.0.0",
        environment=Environment.get_environment(ENVIRONMENT),
        nvm_api_key=os.environ.get("NVM_API_KEY"),
        ai_protocol=True
    )

    # Create an instance of TranslatorAgent
    agent = TranslatorAgent(payment)

    # Start subscription to handle agent tasks
    subscription_task = asyncio.get_event_loop().create_task(
        payment.ai_protocol.subscribe(
            agent.run,
            join_account_room=False,
            join_agent_rooms=[AGENT_DID],
            get_pending_events_on_subscribe=False
        )
    )

    try:
        # Await the subscription task to handle incoming events
        await subscription_task
    except asyncio.CancelledError:
        print("Subscription task was cancelled.")  # Debug: Print cancellation message


# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
