# Template Generator

A Streamlit application for creating, editing, and using templates to generate content with Large Language Models (LLMs).

## Overview

This Template Generator allows you to:

1. Create templates from instructions and uploaded documents
2. Upload and use existing templates
3. Edit templates with a user-friendly interface
4. Generate content using your templates
5. Create synthetic datasets for testing or training

The application leverages OpenAI's LLM models to analyze documents, generate templates, and produce content based on user inputs.

## Getting Started

### Prerequisites

- Python 3.7+
- OpenAI API key

### Installation

1. Clone this repository:
   
   git clone [repository-url]
   cd template-generator
   

2. Install required packages:
   
   pip install -r requirements.txt
   

3. Run the Streamlit app:
   
   streamlit run app.py
   

4. Open your browser and navigate to the URL shown in your terminal (typically http://localhost:8501)

## How to Use

### Setup

1. Enter your OpenAI API key in the sidebar
2. Select your preferred LLM model
3. Choose one of the following options:
   - **Upload existing template**: Upload a previously created template JSON file
   - **Create new template from documents**: Upload documents and provide instructions to generate a new template

### Edit Template

After setting up a template, you can:
- Modify template information (name, version, description)
- Edit the prompt template
- Add, remove, or modify input and output variables
- Download the template as a JSON file for future use

### Use Template

1. Fill in the input fields based on your template's requirements
2. If your template uses a knowledge base, you can view and edit the content
3. Click "Generate Output" to create content using your template
4. View and download the generated output

### Generate Data

1. Specify the number of samples and temperature settings
2. Generate synthetic inputs based on your template's specifications
3. Generate outputs for these inputs
4. Download the complete dataset in CSV or JSON format

## Template Structure

Templates are stored as JSON with the following structure:

```json
{
  "name": "Template Name",
  "version": "1.0.0",
  "description": "Template description",
  "input": [
    {
      "name": "variable_name",
      "description": "Variable description",
      "type": "string/int/float/bool/categorical",
      "min": minimum_value_or_length,
      "max": maximum_value_or_length,
      "options": ["option1", "option2"] (for categorical type)
    }
  ],
  "output": [
    {
      "name": "output_variable_name",
      "description": "Output description",
      "type": "string/int/float/bool/categorical"
    }
  ],
  "prompt": "Template string with {variable_name} placeholders"
}
```


## Features

### Document Processing
- Supports PDF and TXT files
- Extracts text content for use as knowledge base

### Template Generation
- AI-powered template creation based on user instructions
- Automatic identification of input and output variables
- Smart prompt generation

### Template Editing
- User-friendly interface for editing all template components
- AI-assisted prompt rewriting and variation generation

### Content Generation
- Uses OpenAI models to generate content based on templates
- Supports various input types (text, numbers, selections)
- Incorporates knowledge base content when needed

### Synthetic Data Generation
- Creates realistic sample inputs based on template specifications
- Generates corresponding outputs for each input
- Exports complete datasets for testing or training

## Tips for Best Results

1. **Clear Instructions**: When generating templates, provide detailed instructions about what you want to create
2. **Knowledge Base**: Upload relevant documents to improve the quality of generated content
3. **Template Editing**: Review and refine the generated template before use
4. **Prompt Design**: Use the AI rewrite feature to improve your prompt templates
5. **Variable Types**: Choose appropriate types and constraints for your variables

## Troubleshooting

- **API Key Issues**: Ensure your OpenAI API key is entered correctly in the sidebar
- **Template Generation Errors**: Provide more detailed instructions or upload more relevant documents
- **Content Generation Issues**: Review and edit the prompt template to be more specific
- **File Upload Problems**: Check that your files are in supported formats (PDF, TXT)

## Contributing

Please follow internal guidelines for contributing to this project.

## License

This project is licensed for internal use only.