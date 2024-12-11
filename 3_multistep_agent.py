"""
Translator Agent

This module provides a TranslatorAgent class that interacts with OpenAI's GPT-4 API
to translate text, integrating Nevermined payment system and AI protocol.

Classes:
    TranslatorAgent: Handles translation and task execution, including text-to-speech and IPFS integration.
    
Functions:
    main(): Initializes the payment system and the translator agent, then starts the subscription task.
"""

import os
from dotenv import load_dotenv
import asyncio
from payments_py import Payments, Environment
from payments_py.utils import generate_step_id
from payments_py.data_models import AgentExecutionStatus, TaskLog
from utils.openai_tools import OpenAITools
from utils.ipfs_helper import IPFSHelper

# Load environment variables from a .env file for secure configuration management
load_dotenv()

# Constants for API keys and environment setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # API key for OpenAI GPT-4 integration
ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT")  # Environment variable for deployment environment
NVM_API_KEY = os.environ.get("NVM_API_KEY")  # API key for Nevermined system
AGENT_DID = os.environ.get("AGENT_DID")  # Decentralized Identifier for the agent


class TranslatorAgent:
    """
    A class to handle text translation tasks using OpenAI's GPT-4 API.

    Attributes:
        payment (Payments): Instance of the Payments class for task handling and logging.
        openai_tools (OpenAITools): Utility class for interacting with OpenAI models.
    """

    def __init__(self, payment):
        """
        Initializes the TranslatorAgent with the provided payment instance.

        Args:
            payment (Payments): The payment system integration for task and logging management.
        """
        self.payment = payment
        self.openai_tools = OpenAITools(api_key=OPENAI_API_KEY)

    async def run(self, data):
        """
        Executes the translation process for a given task.

        Args:
            data (dict): Dictionary containing task-related information:
                - step_id (str): Identifier for the step to execute.
                - task_id (str): Identifier for the task to execute.
                - did (str): Decentralized identifier (DID) of the agent.

        Raises:
            Exception: Logs and handles errors encountered during the translation process.
        """
        # Retrieve the step details for the current task
        step = self.payment.ai_protocol.get_step(data["step_id"])

        # Validate if the step is pending before proceeding
        if not self._is_step_pending(step):
            return
        
        # Handle steps based on their name (init, translate, or text2speech)
        try:
            step_name = step["name"]
            if step_name == "init":
                await self._handle_init_step(step)
            elif step_name == "translate":
                await self._handle_translate_step(data, step)
            elif step_name == "text2speech":
                await self._handle_text2speech_step(data, step)
            else:
                raise ValueError(f"Unknown step name: {step_name}")
        except Exception as e:
            await self._log_task_error(data["task_id"], f"Error processing step '{step_name}': {str(e)}")

    def _is_step_pending(self, step):
        """
        Checks if the step is in a pending state.
        """
        return step['step_status'] == AgentExecutionStatus.Pending.value
    
    async def _complete_step(self, step, message, output=None, output_artifacts=None):
        """
        Marks a step as completed and logs the completion.
        """
        update_data = {
            "step_id": step["step_id"],
            "task_id": step["task_id"],
            "step_status": AgentExecutionStatus.Completed,
            "output": output or step.get("input_query"),
            "is_last": step.get("is_last", False),
        }
        if output_artifacts:
            update_data["output_artifacts"] = output_artifacts

        self.payment.ai_protocol.update_step(
            did=step["did"],
            task_id=step["task_id"],
            step_id=step["step_id"],
            step=update_data
        )

        if step.get("is_last", False):
            await self._log_task(step["task_id"], message, AgentExecutionStatus.Completed.value)
    
    async def _log_task(self, task_id, message, status=None):
        """
        Logs task events with a specific status.
        """
        task_log = TaskLog(
            task_id=task_id,
            message=message,
            level="info"
        )
        if status:
            task_log.task_status = status

        await self.payment.ai_protocol.log_task(task_log)

    async def _log_task_start(self, task_id, message):
        """
        Logs the start of a task.
        """
        await self._log_task(task_id, message)

    async def _log_task_error(self, task_id, message):
        """
        Logs an error encountered during task execution.
        """
        await self._log_task(task_id, message, AgentExecutionStatus.Failed.value)

    async def _handle_init_step(self, current_step):
        """
        Handles the initialization step, creating subsequent steps.
        """
        translate_step_id = generate_step_id()
        text2speech_step_id = generate_step_id()

        new_steps = [
            {
                "step_id": translate_step_id,
                "task_id": current_step["task_id"],
                "predecessor": current_step["step_id"],
                "name": "translate",
                "is_last": False,
            },
            {
                "step_id": text2speech_step_id,
                "task_id": current_step["task_id"],
                "predecessor": translate_step_id,
                "name": "text2speech",
                "is_last": True,
            }
        ]

        # Create new steps in the AI protocol
        self.payment.ai_protocol.create_steps(
            current_step["did"],
            current_step["task_id"],
            {"steps": new_steps}
        )

        await self._complete_step(current_step, "Init step completed")

    async def _handle_translate_step(self, data, step):
        """
        Handles the translation step, converting text to the target language.
        """
        await self._log_task_start(data["task_id"], "Starting translation")

        try:
            translated_text = self.openai_tools.translate_text(step["input_query"])
            await self._complete_step(step, "Translation complete", output=translated_text)
        except Exception as e:
            raise RuntimeError(f"Translation failed: {str(e)}")
            
    async def _handle_text2speech_step(self, data, step):
        """
        Handles the text-to-speech step, converting text into an audio file and uploading to IPFS.
        """
        await self._log_task_start(data["task_id"], "Starting text-to-speech")

        try:
            file_speech = self.openai_tools.text2speech(step["input_query"])
            ipfs_cid = await IPFSHelper.upload_file_to_ipfs(file_speech)
            ipfs_url = IPFSHelper.get_ipfs_url(ipfs_cid)

            await self._complete_step(
                step,
                "Text-to-speech complete",
                output=f"Speech file uploaded to IPFS at {ipfs_url}",
                output_artifacts=[ipfs_url]
            )
        except Exception as e:
            raise RuntimeError(f"Text-to-speech failed: {str(e)}")

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
        print("Subscription task was cancelled.")


# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
