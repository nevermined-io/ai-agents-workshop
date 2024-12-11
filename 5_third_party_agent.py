"""
Text2Speech Agent

This module provides a Text2SpeechAgent class that converts text into speech using OpenAI's TTS model 
and uploads the resulting audio file to IPFS via a helper class, integrating with Nevermined's AI protocol.

Classes:
    Text2SpeechAgent: Handles text-to-speech tasks and IPFS integration.

Functions:
    main(): Initializes the payment system and the Text2SpeechAgent, then starts the subscription task.
"""

import os
from dotenv import load_dotenv
import asyncio
from payments_py import Payments, Environment
from payments_py.data_models import AgentExecutionStatus, TaskLog
from utils.openai_tools import OpenAITools
from utils.ipfs_helper import IPFSHelper

# Load environment variables from a .env file for secure configuration management
load_dotenv()

# Constants for API keys and environment setup
NVM_API_KEY = os.environ.get("THIRD_PARTY_NVM_API_KEY")  # API key for the Nevermined system
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # API key for OpenAI GPT-4 integration
ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT")  # Deployment environment (e.g., dev, staging, production)
AGENT_DID = os.environ.get("THIRD_PARTY_AGENT_DID")  # Decentralized Identifier (DID) for the agent


class Text2SpeechAgent:
    """
    A class to handle text-to-speech tasks using OpenAI's TTS model and IPFS integration.

    Attributes:
        payment (Payments): Instance of the Payments class for handling tasks and logging.
        openai_tools (OpenAITools): Utility class for interacting with OpenAI's TTS functionality.
    """

    def __init__(self, payment):
        """
        Initializes the Text2SpeechAgent with the given payment system instance.

        Args:
            payment (Payments): The payment system instance used for task handling and logging.
        """
        self.payment = payment
        self.openai_tools = OpenAITools(api_key=OPENAI_API_KEY)

    async def run(self, data):
        """
        Main entry point for the agent to handle incoming tasks.

        Args:
            data (dict): Dictionary containing task-related information:
                - step_id (str): Identifier for the step to execute.
                - task_id (str): Identifier for the task to execute.
                - did (str): Decentralized Identifier (DID) of the agent.
        """
        step = self.payment.ai_protocol.get_step(data["step_id"])

        if not self._is_step_pending(step):
            return

        await self._log_task_start(data["task_id"], "Starting Text2Speech")

        try:
            ipfs_url = await self._process_text2speech(step["input_query"])
            await self._update_step(data, ipfs_url)
            await self._log_task_completion(data["task_id"], "Text2Speech complete")
        except Exception as e:
            await self._log_task_error(data["task_id"], f"Error with Text2Speech: {str(e)}")

    def _is_step_pending(self, step):
        """
        Validates if the step is in a pending state.

        Args:
            step (dict): Step details.

        Returns:
            bool: True if the step is pending, False otherwise.
        """
        return step['step_status'] == AgentExecutionStatus.Pending.value

    async def _process_text2speech(self, input_text):
        """
        Converts input text to speech and uploads the resulting file to IPFS.

        Args:
            input_text (str): The text to be converted to speech.

        Returns:
            str: The IPFS URL of the uploaded audio file.
        """
        try:
            # Convert text to speech
            file_speech = self.openai_tools.text2speech(input_text)

            # Upload the resulting file to IPFS
            ipfs_cid = await IPFSHelper.upload_file_to_ipfs(file_speech)
            ipfs_url = IPFSHelper.get_ipfs_url(ipfs_cid)

            return ipfs_url
        except Exception as e:
            raise RuntimeError(f"Failed to process text-to-speech: {str(e)}")

    async def _update_step(self, data, ipfs_url):
        """
        Updates the step with the IPFS URL and marks it as completed.

        Args:
            data (dict): Task data including DID and task_id.
            ipfs_url (str): The IPFS URL of the uploaded audio file.
        """
        self.payment.ai_protocol.update_step(
            did=data["did"],
            task_id=data["task_id"],
            step_id=data["step_id"],
            step={
                "step_id": data["step_id"],
                "task_id": data["task_id"],
                "step_status": AgentExecutionStatus.Completed,
                "output": ipfs_url,
                "output_artifacts": [ipfs_url],
                "is_last": True
            }
        )

    async def _log_task_start(self, task_id, message):
        """
        Logs the start of a task.

        Args:
            task_id (str): Task identifier.
            message (str): Start message.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message=message,
            level="info",
        ))

    async def _log_task_completion(self, task_id, message):
        """
        Logs the successful completion of a task.

        Args:
            task_id (str): Task identifier.
            message (str): Completion message.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message=message,
            level="info",
            task_status=AgentExecutionStatus.Completed
        ))

    async def _log_task_error(self, task_id, error_message):
        """
        Logs an error encountered during task execution.

        Args:
            task_id (str): Task identifier.
            error_message (str): Error message to log.
        """
        await self.payment.ai_protocol.log_task(TaskLog(
            task_id=task_id,
            message=error_message,
            level="error",
            task_status=AgentExecutionStatus.Failed
        ))


async def main():
    """
    Main function to initialize the Text2SpeechAgent and handle subscription tasks.

    This function:
        - Initializes the payment system.
        - Creates a Text2SpeechAgent instance.
        - Starts the subscription task for the agent.
    """
    # Initialize the payment system
    payment = Payments(
        app_id="text2speech_agent",
        version="1.0.0",
        environment=Environment.get_environment(ENVIRONMENT),
        nvm_api_key=NVM_API_KEY,
        ai_protocol=True
    )

    # Create an instance of the Text2SpeechAgent
    agent = Text2SpeechAgent(payment)

    # Start the subscription task to process incoming events
    subscription_task = asyncio.get_event_loop().create_task(
        payment.ai_protocol.subscribe(
            agent.run,
            join_account_room=False,
            join_agent_rooms=[AGENT_DID],
            get_pending_events_on_subscribe=False
        )
    )

    try:
        # Wait for the subscription task to handle events asynchronously
        await subscription_task
    except asyncio.CancelledError:
        print("Subscription task was cancelled.")  # Debug message when task is cancelled


# Entry point for the script
if __name__ == "__main__":
    asyncio.run(main())
