# 🔮 MagicCSV

MagicCSV is a Streamlit-based application that leverages local Ollama LLMs to add a new column to your CSV files using customizable prompts.

## 🚀 Quick Start (for Users)

1. Download the `MagicCSV.exe` from the `./dist` folder.
2. Ensure Ollama is installed and running on your system.
3. Double-click `MagicCSV.exe` to launch the application.
4. Upload your CSV, configure settings, and process your data!

## 🛠️ Development Setup

### Running the Streamlit App

1. Clone the repository:

```console
git clone https://github.com/neovand/MagicCSV.git
cd MagicCSV
```

2. Create and activate a virtual environment:

```console
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

3. Install dependencies:

```console
pip install -r requirements.txt
```
4. Run the Streamlit app:

```console
streamlit run app.py
```

### Building the Executable

1. Install PyInstaller:
```console
pip install pyinstaller
```

2. Build the executable:
```console
pyinstaller run.spec --clean
```

## 📝 Todo
- [x] Ollama Integration
- [x] Build for Windows
- [ ] OpenAI, Anthropic, Groq Integration
- [ ] Build for Mac and Linux
- [ ] Add batch processing capabilities
- [ ] Implement prompts that can access other rows, not just the current row
- [ ] Add support for more file formats (e.g., Excel, JSON)
- [ ] Implement error handling and logging
- [ ] Create user documentation and usage examples