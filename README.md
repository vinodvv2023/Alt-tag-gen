# Alt-tag-gen
Image Accessibility Enhancer A powerful, flexible tool that generates rich, descriptive text for images to improve web accessibility. This application uses state-of-the-art Large Language Models (LLMs) to provide context-aware descriptions for both local and web-based images, making visual content accessible to everyone.

Features
Flexible Image Input: Process images directly from your local file system or by providing a web URL by read an excel file or by just parsing all the images folder of the app.

Multiple AI Backends: Seamlessly switch between different inference providers:

Ollama: Run powerful models like LLaVA locally for full privacy and control.

Hugging Face: Access thousands of cutting-edge vision models via the transformers library or the Hugging Face Inference API.

High-Quality Descriptions: Generates detailed, human-like descriptions that go beyond simple object labels, capturing context, actions, and relationships within the image.

Easy to Integrate: Use it as a standalone command-line tool, a lightweight web service, or integrate it as a library into your existing applications.

Customizable: Easily configure the model, prompts, and output format to suit your specific needs.

⚙️ How It Works
The application follows a simple yet powerful pipeline:

Image Loading: The user provides an image either as a local file path or a public URL. The app fetches and preprocesses the image.

Model Inference: The processed image is sent to the configured Large Language Model backend (Ollama, Hugging Face, etc.).

Description Generation: The vision-language model analyzes the image and generates a descriptive text caption based on its visual content.

Output: The generated description is returned to the user in the web UI, ready to be used as alt-text, for accessibility services, or content analysis. Other option is to provide the excel file with the generated content for the respective image. or provide the html page, app find the image filename adds the alt tag with description.
