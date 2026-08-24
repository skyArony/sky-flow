---
name: eli5
description: Explain a topic like I'm a 5 year old. Use when the user invokes /eli5 with a topic or asks for a dead-simple picture explainer of how something works.
---

# eli5

Explain like I'm someone who knows nothing about this topic, using a HTML artifact with big pictures and few words.

After creating the page, always start a non-blocking local web server rooted at the artifact directory. Choose an available port, bind it to `127.0.0.1`, verify that the page loads over HTTP, and return the clickable `http://127.0.0.1:<port>/...` URL as the deliverable. Do not return the HTML file path instead of the URL.

Topic: $ARGUMENTS
