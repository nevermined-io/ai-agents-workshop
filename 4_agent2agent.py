"""
Translator Agent

This module provides a TranslatorAgent class that interacts with OpenAI's GPT-4 API
to translate text, integrating Nevermined payment system and AI protocol.

Classes:
    TranslatorAgent: Handles translation and task execution, including text-to-speech and IPFS integration.
    
Functions:
    main(): Initializes the payment system and the translator agent, then starts the subscription task.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv
import asyncio
from payments_py import Payments, Environment
from payments_py.utils import generate_step_id
from payments_py.data_models import AgentExecutionStatus, TaskLog
from utils.openai_tools import OpenAITools
import json

# Load environment variables from a .env file for secure configuration management
load_dotenv()

# Constants for API keys and environment setup
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")  # API key for OpenAI GPT-4 integration
ENVIRONMENT = os.environ.get("NVM_ENVIRONMENT")  # Environment variable for deployment environment
NVM_API_KEY = os.environ.get("NVM_API_KEY")  # API key for Nevermined system
AGENT_DID = os.environ.get("AGENT_DID")  # Decentralized Identifier for the agent

THIRD_PARTY_PLAN_DID = os.environ.get("THIRD_PARTY_PLAN_DID")  # DID of the third-party agent's plan
THIRD_PARTY_AGENT_DID = os.environ.get("THIRD_PARTY_AGENT_DID")  # DID of the text-to-speech agent

class TranslatorAgent:
    """
    A class to handle text translation tasks using OpenAI's GPT-4 API and delegate tasks like text-to-speech
    to third-party agents using Nevermined's AI protocol.

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
        Main orchestrator function to execute tasks based on the step type.

        Args:
            data (dict): Dictionary containing task-related information:
                - step_id (str): Identifier for the step to execute.
                - task_id (str): Identifier for the overall task.
                - did (str): Decentralized identifier (DID) of the agent.

        Raises:
            Exception: Logs and handles errors encountered during task execution.
        """
        # Retrieve step details from the AI protocol
        step = self.payment.ai_protocol.get_step(data["step_id"])

        # Check if the step is in a pending state
        if not self._is_step_pending(step):
            return

        try:
            # Determine the type of step and delegate to the appropriate handler
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
            # Log errors encountered during step processing
            await self._log_task_error(data["task_id"], f"Error processing step '{step_name}': {str(e)}")

    def _is_step_pending(self, step):
        """
        Checks if a step is in a pending state.

        Args:
            step (dict): Step details.

        Returns:
            bool: True if the step is pending, False otherwise.
        """
        return step['step_status'] == AgentExecutionStatus.Pending.value

    async def _handle_init_step(self, step):
        """
        Handles the initialization step by creating subsequent steps for translation and text-to-speech.

        Args:
            step (dict): Details of the initialization step.
        """
        # Generate unique identifiers for the subsequent steps
        translate_step_id = generate_step_id()
        text2speech_step_id = generate_step_id()

        # Define the workflow steps
        steps = [
            {
                "step_id": translate_step_id,
                "task_id": step["task_id"],
                "predecessor": step["step_id"],
                "name": "translate",
                "is_last": False,  # Indicates this is not the last step
            },
            {
                "step_id": text2speech_step_id,
                "task_id": step["task_id"],
                "predecessor": translate_step_id,
                "name": "text2speech",
                "is_last": True,  # Indicates this is the last step
            }
        ]

        # Register the steps in the AI protocol
        self.payment.ai_protocol.create_steps(
            step["did"],
            step["task_id"],
            {"steps": steps}
        )

        # Mark the initialization step as completed
        await self._complete_step(step, "Init step completed")

    async def _handle_translate_step(self, data, step):
        """
        Handles the translation step by translating input text to the target language.

        Args:
            data (dict): Task data including DID and task_id.
            step (dict): Details of the translation step.
        """
        # Log the start of the translation process
        await self._log_task_start(data["task_id"], "Starting translation")

        try:
            # Perform the translation using OpenAI tools
            translated_text = self.openai_tools.translate_text(step["input_query"])

            # Mark the step as completed with the translation output
            await self._complete_step(step, "Translation complete", output=translated_text)
        except Exception as e:
            # Raise a runtime error if the translation fails
            raise RuntimeError(f"Translation failed: {str(e)}")

    async def _handle_text2speech_step(self, data, step):
        """
        Handles the text-to-speech step by delegating it to a third-party agent.

        Args:
            data (dict): Task data including DID and task_id.
            step (dict): Details of the text-to-speech step.
        """
        # Log the start of the text-to-speech process
        await self._log_task_start(data["task_id"], "Starting text-to-speech")

        # Ensure sufficient balance for the third-party agent
        if not await self._ensure_sufficient_balance(THIRD_PARTY_PLAN_DID):
            await self._log_task_error(data["task_id"], "Insufficient balance for third-party plan")
            return

        # Define the data to send to the third-party agent
        task_data = {
            "query": step["input_query"],  # Text to be converted to speech
            "name": step["name"],
            "additional_params": [],
            "artifacts": []
        }

        # Define a callback to handle the response from the third-party agent
        async def task_callback(callback_data):
            task_log = json.loads(callback_data)
            if task_log.get('task_status', None) == AgentExecutionStatus.Completed.value:
                await self._subtask_finished(task_log["task_id"], step)
            elif task_log.get('task_status', None) == AgentExecutionStatus.Failed.value:
                await self._log_task_error(data["task_id"], f"Error in subtask: {task_log.get('message', '')}")
            else:
                await self._log_task(data["task_id"], task_log.get('message', ''), task_log.get('task_status', None))

        # Create the task with the third-party agent
        result = await self.payment.ai_protocol.create_task(
            THIRD_PARTY_AGENT_DID,
            task_data,
            task_callback
        )

        # Handle the response from the task creation
        if result.status_code == 201:
            created_task = result.json()
            await self._log_task(
                data["task_id"],
                f"Subtask with id {created_task['task']['task_id']} created successfully",
                AgentExecutionStatus.In_Progress
            )
            # Update status to don't be processed twice if the response take long
            self.payment.ai_protocol.update_step(
                step["did"],
                step["task_id"],
                step_id=step["step_id"],
                step={"step_status": AgentExecutionStatus.In_Progress.value}
            )
            
        else:
            # Log an error if the subtask creation fails
            await self._log_task_error(data["task_id"], f"Error creating subtask: {result.text}")

    async def _subtask_finished(self, subtask_id, step):
        """
        Handles the completion of a subtask by updating the main step with the results.

        Args:
            subtask_id (str): Identifier for the subtask.
            step (dict): Details of the main step.
        """
        # Retrieve the subtask result from the AI protocol
        subtask_result = self.payment.ai_protocol.get_task_with_steps(THIRD_PARTY_AGENT_DID, subtask_id)
        subtask_data = subtask_result.json()
        
        # Determine the status of the subtask
        status = (
            AgentExecutionStatus.Completed.value
            if subtask_data["task"]["task_status"] == "Completed"
            else AgentExecutionStatus.Failed.value
        )

        # Mark the main step as completed or failed with the subtask's output
        return await self._complete_step(
            step,
            f"Subtask {'completed' if status == AgentExecutionStatus.Completed.value else 'failed'}",
            output=subtask_data["task"].get("output", ""),
            output_artifacts=subtask_data["task"].get("output_artifacts", [])
        )

    async def _ensure_sufficient_balance(self, plan_did):
        """
        Ensures there is sufficient balance for the specified plan.

        Args:
            plan_did (str): Identifier of the plan.

        Returns:
            bool: True if sufficient balance is available, False otherwise.
        """
        # Check the balance for the plan
        balance = self.payment.get_plan_balance(plan_did)

        # Order additional credits if balance is insufficient
        if int(balance.balance) < 1:
            response = self.payment.order_plan(plan_did)
            return response.success
        return True

    async def _complete_step(self, step, message, output=None, output_artifacts=None):
        """
        Marks a step as completed and logs the completion.

        Args:
            step (dict): Details of the step to complete.
            message (str): Completion message.
            output (str, optional): Output of the step. Defaults to None.
            output_artifacts (list, optional): Artifacts produced by the step. Defaults to None.
        """
        # Prepare the step update data
        update_data = {
            "step_status": AgentExecutionStatus.Completed.value,
            "output": output or step.get("input_query"),
            "is_last": step.get("is_last", False),
        }
        if output_artifacts:
            update_data["output_artifacts"] = output_artifacts

        # Update the step in the AI protocol
        self.payment.ai_protocol.update_step(
            step["did"],
            step["task_id"],
            step_id=step["step_id"],
            step=update_data
        )

        # Log the completion of the step
        if step.get("is_last", False):
            await self._log_task(step["task_id"], message, AgentExecutionStatus.Completed)

    async def _log_task(self, task_id, message, status=None):
        """
        Logs a task event with a specific status.

        Args:
            task_id (str): Task identifier.
            message (str): Log message.
            status (str, optional): Task status. Defaults to None.
        """
        task_log = TaskLog(task_id=task_id, message=message, level="info")
        if status:
            task_log.task_status = status
        await self.payment.ai_protocol.log_task(task_log)

    async def _log_task_start(self, task_id, message):
        """
        Logs the start of a task.

        Args:
            task_id (str): Task identifier.
            message (str): Start message.
        """
        await self._log_task(task_id, message, AgentExecutionStatus.Pending)

    async def _log_task_error(self, task_id, message):
        """
        Logs an error encountered during task execution.

        Args:
            task_id (str): Task identifier.
            message (str): Error message.
        """
        await self._log_task(task_id, message, AgentExecutionStatus.Failed)



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
