[🏠 Back to Roadmap](ROADMAP.md)

---

# 📖 The "No Detail Too Small" Glossary & Structure Guide

As a beginner, it is easy to get lost in the "small" details of a codebase. This document explains every single folder, library, and small concept we are using, no matter how tiny!

## 📁 Project Directory Structure

### `app/templates/` (The Jinja2 Directory)
**What is it?** This is the directory where we store our HTML files for the Universal Dashboard. 
**Why do we need it?** When you use a modern frontend framework like React, the frontend and backend are completely separate. But sometimes, you just want the backend Python server to render a quick HTML page directly. **Jinja2** is a tool that lets FastAPI take an HTML file from this directory, inject Python variables into it (like our meeting transcripts), and send the final HTML to the user's browser.
**How it works in code:** `templates = Jinja2Templates(directory="app/templates")` tells FastAPI to look inside this specific folder anytime we want to render an HTML page.

### `requirements.txt`
**What is it?** A simple text file that lists all the external libraries our project needs to run. 
**Why do we need it?** If you give this project to a friend, their Python doesn't have FastAPI or Redis installed yet. They just run `pip install -r requirements.txt` and it downloads exactly what they need.

---

## 🧩 The Small Concepts (Chunk by Chunk)

### From Chunk 1: FastAPI & Async
* **`@app.get(...)`**: This is called a **Decorator**. It is a shortcut that tells FastAPI, "If a user goes to this URL in their browser, run the function right underneath this line."
* **`async def`**: This tells Python that the function is capable of pausing its execution (yielding) while it waits for something slow (like a database or network request), allowing the server to do other things in the meantime.
* **`await`**: This is the actual pause button. You put it in front of slow tasks to tell Python, "Wait here for this to finish, but go help other users while you wait."

### From Chunk 2: WebSockets & Backpressure
* **`websocket.accept()`**: Unlike a standard website visit, a WebSocket is a phone call. When the client "calls" the server, the server must explicitly "pick up the phone" using this command before they can talk.
* **`asyncio.Queue(maxsize=100)`**: This is our memory bucket. The `maxsize` is critical! If we didn't have a max size, a hacker could send us 10 million audio packets in one second, fill up our server's RAM, and crash the whole application.
* **`queue.task_done()`**: When our background worker finishes processing an audio packet from the bucket, it calls this to tell the bucket, "I successfully handled that item." This is required to keep the bucket's internal counter accurate.

### From Chunk 3: Redis & Jinja2
* **`decode_responses=True`**: When Redis stores data, it saves it as raw bytes (like `b'Hello'`). Passing this flag tells Redis to automatically convert those bytes back into normal Python strings (`'Hello'`) when we read them, saving us a lot of headache.
* **`time.time()`**: A built-in Python function that returns the current time in seconds since January 1, 1970 (e.g., `1700000000.12`). We use this precise decimal number as the "Score" in our Redis list so things are perfectly ordered.
* **`json.loads(row)`**: Redis stores our timeline entries as strings (text). We use this to turn that text string back into a real Python Dictionary so we can access `data["speaker"]`.
* **`HTMLResponse`**: Tells FastAPI that instead of sending back JSON data (like an API usually does), we are sending back a full webpage that the browser should render visually.
* **`TemplateResponse("mom.html", {"timeline": ...})`**: This takes our `mom.html` file out of the `app/templates` directory, injects the live timeline data into it, and serves it to the user.

---

[🏠 Back to Roadmap](ROADMAP.md)
