Here’s a clear and detailed README for your project, based on your code and the initial README content:

---

# Athlete Assistant – Front Desk Agent

## Overview

**Athlete Assistant** is an AI-powered front desk chatbot designed to help athletes, coaches, and customers with schedule management, event creation, and sports-related information. It uses multiple specialized agents to understand user intent, generate SQL queries, answer knowledge-based questions, and provide friendly, professional responses.

---

## Features

- **Intent Recognition:**  
  Determines whether a user’s message is about schedules (database queries) or general sports knowledge.

- **SQL Agent (NLP2SQL):**  
  Converts natural language queries into SQL to fetch or update athlete and coach schedules.

- **Knowledge Agent:**  
  Answers questions about sports rules, strategies, and official news.

- **Front Desk Agent:**  
  Acts as the main interface, greeting users, clarifying requests, and routing queries to the appropriate specialist agent.

- **Moderator Agent:**  
  Rephrases agent responses to be clear, friendly, and easy to understand.

- **Gradio Web Interface:**  
  Provides a user-friendly chat interface for interaction.

---

## How It Works

1. **User Interaction:**  
   Users type messages into the chat interface.

2. **Intent Detection:**  
   The system uses the Intent Judge agent to classify the message as a schedule/database query, a knowledge question, or both.

3. **Specialist Handling:**  
   - If it’s a schedule-related query, the SQL Agent generates an SQL query, which is executed against the database.
   - If it’s a knowledge question, the Knowledge Agent provides an answer.
   - The Moderator Agent refines responses for clarity and friendliness.

4. **Front Desk Response:**  
   The Front Desk Agent communicates the final answer to the user, ensuring a professional and helpful experience.

---

## Agents Breakdown

- **Intent Judge:**  
  Classifies user intent for routing.

- **SQL Agent:**  
  - Converts natural language to SQL for the `athlete_batches` table.
  - Handles event/session creation, updates, and schedule reporting.

- **Knowledge Agent:**  
  - Answers only sports-related questions (rules, strategies, official news).
  - Politely declines unrelated queries.

- **Front Desk Agent:**  
  - Greets users, clarifies requests, and routes to specialists.
  - Ensures a smooth, respectful conversation.

- **Moderator Agent:**  
  - Refines agent responses for clarity and tone.

---

## Database Schema

The main table used is:

```sql
CREATE TABLE public.athlete_batches (
    id serial4 PRIMARY KEY,
    contact_no varchar(15) NOT NULL,
    athlete_name text NOT NULL,
    batch_name text NOT NULL,
    "date" date NOT NULL,
    start_time time NOT NULL,
    end_time time NOT NULL,
    status varchar(10) NOT NULL CHECK (status IN ('Open', 'Cancelled'))
);
```

---

## Setup & Usage

1. **Install Dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Configure Environment:**
   - Create a `.env` file with your database credentials.

3. **Run the App:**
   ```
   python main.py
   ```
   - This will launch the Gradio web interface.

4. **Interact:**
   - Open the provided URL in your browser and start chatting!

---

## Example Queries

- “What is my training schedule for next week?”
- “Can you add a session for John on Friday?”
- “What are the official rules for basketball?”
- “Update the status of today’s session to cancelled.”

---

## Notes

- The system is designed for **sports-related queries only**.
- For best results, ensure your database is set up as per the schema above.

---

## Contributing

Pull requests and suggestions are welcome! Please ensure any new features align with the project’s focus on athlete and coach support.

---

## License

MIT License

---

Let me know if you want this saved as a file or need further customization!
