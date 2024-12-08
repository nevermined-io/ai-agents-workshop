[![banner](https://raw.githubusercontent.com/nevermined-io/assets/main/images/logo/banner_logo.png)](https://nevermined.io)


**Nevermined AI Agents Workshop: From Basics to Advanced**
==========================================================

This repository is designed as a workshop to progressively build AI agents, starting from a simple translator using OpenAI's API to a complex multi-step agent that integrates with the Nevermined payment system and delegates tasks to external agents.

**Workshop Structure**
----------------------

The workshop consists of 5 stages, each represented by a separate Python file. Each stage builds upon the previous one, introducing new concepts and functionalities:

1.  **Basic Agent (`1_simple_agent.py`)**: A standalone translator agent using OpenAI's GPT-4 API.
2.  **Agent with Payment Integration (`2_agent_with_payment.py`)**: Adds Nevermined payment system integration for managing tasks.
3.  **Multi-step Agent (`3_multistep_agent.py`)**: Handles workflows with multiple steps, including translation and text-to-speech.
4.  **Agent-to-Agent Communication (`4_agent2agent.py`)**: Delegates tasks (e.g., text-to-speech) to an external agent.
5.  **Third-Party Agent (`5_third_party_agent.py`)**: Implements the external agent used in the fourth stage for text-to-speech tasks.

* * *

**Setup Instructions**
----------------------

### **1\. Clone the repository**

```bash
git clone https://github.com/nevermined-io/ai-agents-workshop.git
cd ai-agents-workshop
```

### **2\. Create a Python virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **3\. Install dependencies**

Install the required Python libraries:

```bash
pip install -r requirements.txt
```

### **4\. Configure environment variables**

Copy the example `.env` file and fill in your credentials:

```bash
cp .env.example .env
```

Set the following keys in the `.env` file:

```env
NVM_API_KEY=your_nevermined_api_key
NVM_ENVIRONMENT=development  # Use "staging" or "production" as needed

AGENT_DID=your_agent_did
THIRD_PARTY_AGENT_DID=third_party_agent_did
THIRD_PARTY_PLAN_DID=third_party_plan_did
THIRD_PARTY_NVM_API_KEY=third_party_nvm_api_key

OPENAI_API_KEY=your_openai_api_key
PINATA_API_KEY=your_pinata_ipfs_api_key
PINATA_API_SECRET=your_pinata_ipfs_api_secret
```

* * *

**Workshop Files Overview**
---------------------------

### **1\. `1_simple_agent.py`**

This is the starting point of the workshop. The `1_simple_agent.py` script implements a basic translator that uses OpenAI's GPT-4 API to translate text from one language to another.

#### **Steps to Complete the Example:**

1.  Open the `1_simple_agent.py` file and review the `translate_text` function.
    *   This function takes input text, the source language, and the target language.
    *   It sends a request to OpenAI's API to generate the translation.
2.  Run the script:
    
    ```bash
    python 1_simple_agent.py
    ```
    
3.  The script will print the translation of a predefined English sentence into French.

This script does not require any integration beyond OpenAI and demonstrates a simple workflow.

* * *

### **2\. `2_agent_with_payment.py`**

In this stage, we extend the functionality of the agent by integrating the Nevermined payment system. The agent now manages tasks through the Nevermined AI protocol, ensuring proper logging and task state management.

#### **Steps to Complete the Example:**

1.  Open the `2_agent_with_payment.py` file and explore the `TranslatorAgent` class.
    *   The agent retrieves tasks via the Nevermined protocol and processes them step-by-step.
    *   Task states are logged and updated using the `log_task` and `update_step` methods.
2.  Ensure your `.env` file contains valid Nevermined credentials and an agent DID.
3.  Start the agent by running:
    
    ```bash
    python 2_agent_with_payment.py
    ```
    
4.  Use Nevermined's AI protocol to send a translation task to the agent.

The output will include task logs and the translated text.

* * *

### **3\. `3_multistep_agent.py`**

This script introduces the concept of multi-step workflows. The agent handles tasks that require multiple steps, such as:

1.  Translating text.
2.  Converting the translated text to speech.
3.  Uploading the speech file to IPFS.

#### **Steps to Complete the Example:**

1.  Open the `3_multistep_agent.py` file and review the `TranslatorAgent` class.
    *   Note the `run` method, which orchestrates the workflow by identifying and executing steps (e.g., `translate` and `text2speech`).
    *   The agent uses helper functions from `utils/openai_tools.py` and `utils/ipfs_helper.py` for text-to-speech conversion and IPFS integration.
2.  Run the agent:
    
    ```bash
    python 3_multistep_agent.py
    ```
    
3.  Send a multi-step task to the agent via the Nevermined AI protocol.
    *   Include a query for translation, which will trigger subsequent steps (e.g., text-to-speech and IPFS upload).
4.  Observe the task progress and final output, including the IPFS URL of the generated audio file.

* * *

### **4\. `4_agent2agent.py`**

This stage focuses on delegating tasks to another agent. The `4_agent2agent.py` script implements an agent that performs translation but delegates the text-to-speech step to an external agent via the Nevermined AI protocol.

#### **Steps to Complete the Example:**

1.  Open the `4_agent2agent.py` file and review how tasks are divided between the main agent and the external agent.
    *   The `handle_text2speech_step` method creates a subtask for the external agent and processes its response.
    *   The `THIRD_PARTY_AGENT_DID` environment variable specifies the external agent.
2.  Ensure the external agent (`5_third_party_agent.py`) is running and accessible:
    ```bash
    python 5_third_party_agent.py
    ```
    
3.  Start the agent:
    
    ```bash
    python 4_agent2agent.py
    ```
    
4.  Send a task with a text input for translation. The text-to-speech conversion will be handled by the external agent.
5.  Observe the task logs and the final output, including the audio file’s IPFS URL in `output_artifacts`.

* * *

### **5\. `5_third_party_agent.py`**

This is the external agent responsible for handling text-to-speech tasks. It converts input text to speech using OpenAI's TTS API and uploads the resulting audio file to IPFS.

#### **Steps to Complete the Example:**

1.  Open the `5_third_party_agent.py` file and review the `Text2SpeechAgent` class.
    *   The `run` method processes tasks and generates audio files.
    *   The `_process_text2speech` method uses OpenAI's TTS API and IPFS helper utilities.
2.  Ensure your `.env` file includes credentials for the external agent (`THIRD_PARTY_NVM_API_KEY` and `THIRD_PARTY_AGENT_DID`).
3.  Start the external agent:
    
    ```bash
    python 5_third_party_agent.py
    ```
    
4.  Use the main agent (`4_agent2agent.py`) to send a text-to-speech task to this external agent.
5.  Verify the task's completion by checking the logs and IPFS output.

* * *

**Supporting Files**
--------------------

### **`utils/openai_tools.py`**

This file contains helper functions for interacting with OpenAI's API, including:

*   Text translation.
*   Text-to-speech conversion.

### **`utils/ipfs_helper.py`**

Provides utility functions for uploading files to IPFS and retrieving public URLs for the uploaded content.

### **`requirements.txt`**

Lists the dependencies for the project, including:

*   `openai` for API interactions.
*   `payments_py` for Nevermined integration.
*   `dotenv` for managing environment variables.

### **`.env.example`**

An example environment variable file showing the required keys for the agents.

* * *

**Project Structure**
---------------------

```bash
ai-agents-workshop/
│
├── 1_simple_agent.py         # Basic translator using OpenAI
├── 2_agent_with_payment.py   # Adds Nevermined payment system
├── 3_multistep_agent.py      # Multi-step translation and TTS agent
├── 4_agent2agent.py          # Delegates TTS to an external agent
├── 5_third_party_agent.py    # Third-party text-to-speech agent
├── utils/
│   ├── openai_tools.py       # Helper functions for OpenAI
│   ├── ipfs_helper.py        # Helper functions for IPFS
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
├── .env.example              # Example environment variable file
└── README.md                 # Documentation
```

* * *

License
-------

```
Copyright 2024 Nevermined AG

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```