# Template Generator

A Streamlit application for creating, editing, and using templates to generate content and synthetic data with Large Language Models (LLMs).

## Overview

This Template Generator allows you to:

1. Create templates from instructions and uploaded documents
2. Create templates from tabular data (CSV, Excel, JSON)
3. Upload and use existing templates
4. Edit templates with a user-friendly interface
5. Generate content using your templates
6. Create synthetic datasets for testing or training
7. Augment existing data tables with AI-generated content

The application leverages OpenAI and Anthropic LLM models to analyze documents, generate templates, and produce content based on user inputs.

## Getting Started

### Prerequisites

- Python 3.10+
- OpenAI API key or Anthropic API key

### Installation

1. Clone this repository:
```
git clone [repository-url] cd template-generator
```

2. Install required packages:
```
pip install -r requirements.txt
```

3. Run the Streamlit app:
```
streamlit run app.py
```

4. Open your browser and navigate to the URL shown in your terminal (typically http://localhost:8501)

## How to Use

### Setup

1. Enter your OpenAI or Anthropic API key in the sidebar
2. Select your preferred LLM model
3. Choose one of the following options:
- **Create new template from documents**: Upload documents and provide instructions to generate a new template
- **Create template from tabular data**: Upload a CSV, Excel, or JSON file to create a template based on its structure
- **Upload existing template**: Upload a previously created template JSON file
- **Create an empty template**: Start with a minimal template that you can customize

### Edit Template

After setting up a template, you can:
- Modify template information (name, version, description)
- Edit the prompt template with AI assistance (rewrite or generate variations)
- Add, remove, or modify input and output variables
- Manage categorical variables with options
- Analyze your knowledge base to suggest variables and values
- Integrate with uploaded data tables
- Download the template as a JSON file for future use

### Generate Data

1. Specify the number of samples and temperature settings
2. Configure categorical variable options for permutations
3. Use data from uploaded tables or generate synthetic inputs
4. Generate outputs for all samples or selected samples
5. Generate multiple output variations for selected inputs
6. Compare generated outputs with original data
7. Download the complete dataset in CSV, JSON, or Parquet format

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
- Supports PDF, TXT, DOCX, and HTML files
- Extracts text content for use as knowledge base
- Analyzes knowledge base to suggest variables and values

### Tabular Data Integration
- Create templates from CSV, Excel, or JSON files
- Use existing data tables as input sources
- Augment tables with AI-generated missing columns
- Compare generated outputs with original data

### Template Generation
- AI-powered template creation based on user instructions
- Automatic identification of input and output variables
- Smart prompt generation
- Categorical variable management with option suggestions

### Template Editing
- User-friendly interface for editing all template components
- AI-assisted prompt rewriting and variation generation
- Knowledge base management and analysis
- Variable suggestion from document content

### Content Generation
- Uses OpenAI or Anthropic models to generate content based on templates
- Supports various input types (text, numbers, selections)
- Incorporates knowledge base content when needed
- Preview prompts before generation

### Synthetic Data Generation
- Creates realistic sample inputs based on template specifications
- Generates corresponding outputs for each input
- Supports categorical variable permutations
- Generates multiple output variations for diversity
- Exports complete datasets in CSV, JSON, or Parquet formats

## Tips for Best Results

1. **Clear Instructions**: When generating templates, provide detailed instructions about what you want to create
2. **Knowledge Base**: Upload relevant documents to improve the quality of generated content
3. **Template Editing**: Review and refine the generated template before use
4. **Prompt Design**: Use the AI rewrite feature to improve your prompt templates
5. **Variable Types**: Choose appropriate types and constraints for your variables
6. **Categorical Variables**: Define comprehensive options for categorical variables
7. **Data Tables**: Use existing data tables to guide the generation process

## Troubleshooting

- **API Key Issues**: Ensure your OpenAI or Anthropic API key is entered correctly in the sidebar
- **Template Generation Errors**: Provide more detailed instructions or upload more relevant documents
- **Content Generation Issues**: Review and edit the prompt template to be more specific
- **File Upload Problems**: Check that your files are in supported formats
- **Categorical Permutations**: If you have many categorical variables with many options, the number of possible combinations can grow very large

## TODO

- Add unit tests for template generation and content creation functionalities
- Improve error handling for file uploads and API key validation
- Add functionality for creating new rows for synthetic data generation on existing tables