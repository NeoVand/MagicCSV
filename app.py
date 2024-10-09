import streamlit as st
import pandas as pd
import requests
import json
import time
import random
from datetime import timedelta
import html
from textcomplete import textcomplete, StrategyProps

# Default Ollama URL
DEFAULT_OLLAMA_URL = 'http://localhost:11434'

def check_ollama_connection(ollama_url):
    try:
        requests.get(f'{ollama_url}/api/tags', timeout=5).raise_for_status()
        return True
    except requests.RequestException:
        return False

@st.cache_data
def get_ollama_models(ollama_url):
    try:
        response = requests.get(f'{ollama_url}/api/tags', timeout=5)
        response.raise_for_status()
        return [model['name'] for model in response.json()['models']]
    except requests.RequestException as e:
        return []

def init_session_state():
    if 'df' not in st.session_state:
        st.session_state.df = None
    if 'processed_columns' not in st.session_state:
        st.session_state.processed_columns = []
    if 'ollama_url' not in st.session_state:
        st.session_state.ollama_url = DEFAULT_OLLAMA_URL
    if 'model_settings' not in st.session_state:
        st.session_state.model_settings = {
            'temperature': 0.8,
            'top_p': 0.9,
            'top_k': 40,
            'min_p': 0.05,
            'repeat_penalty': 1.1,
            'repeat_last_n': 64,
            'num_predict': 128,
            'stop': '',
            'tfs_z': 1.0,
            'mirostat_mode': 0,
            'mirostat_tau': 5.0,
            'mirostat_eta': 0.1,
            'num_ctx': 2048,
            'seed': 0,
            'system_prompt': ''
        }
    if 'prompt_template' not in st.session_state:
        st.session_state.prompt_template = ''

def generate_output(ollama_url, model, prompt, options):
    try:
        data = {
            'model': model,
            'prompt': prompt,
            'options': options
        }
        response = requests.post(f'{ollama_url}/api/generate', 
                                 json=data,
                                 stream=True,
                                 timeout=30)
        response.raise_for_status()
        
        return response
    except requests.RequestException as e:
        st.error(f"Error calling Ollama API: {str(e)}")
        return None

def format_time(seconds):
    return str(timedelta(seconds=int(seconds)))

@st.cache_data
def load_csv(file):
    return pd.read_csv(file)

def main():
    st.set_page_config(page_title="MagicCSV", page_icon="🔮", layout="wide")
    init_session_state()

    st.sidebar.markdown("# 🔮 MagicCSV")

    with st.sidebar.expander("🛠️ Model Settings", expanded=False):
        ollama_url = st.text_input("Ollama Server URL:", value=st.session_state.ollama_url, key="ollama_url_input")
        if ollama_url != st.session_state.ollama_url:
            st.session_state.ollama_url = ollama_url

        if not check_ollama_connection(st.session_state.ollama_url):
            st.error(f"Cannot connect to Ollama server at {st.session_state.ollama_url}. Please make sure it's running.")
            st.warning("If you're using Docker, try changing the Ollama Server URL to 'http://host.docker.internal:11434' or your Docker host IP.")
        else:
            models = get_ollama_models(st.session_state.ollama_url)
            if not models:
                st.error("No Ollama models available. Please check your Ollama installation.")
            else:
                model = st.selectbox('Select Ollama Model:', models, key="model_select")
                
                # Advanced Model Settings
                st.markdown("### Advanced Model Settings")
                
                for key, value in st.session_state.model_settings.items():
                    if key in ['temperature', 'top_p', 'min_p', 'repeat_penalty', 'tfs_z', 'mirostat_tau', 'mirostat_eta']:
                        st.session_state.model_settings[key] = st.slider(key.capitalize(), min_value=0.0, max_value=2.0, value=value, step=0.1, key=f"slider_{key}")
                    elif key in ['top_k', 'repeat_last_n', 'num_ctx']:
                        st.session_state.model_settings[key] = st.slider(key.capitalize(), min_value=1, max_value=2048, value=value, key=f"slider_{key}")
                    elif key == 'num_predict':
                        st.session_state.model_settings[key] = st.number_input('Number of Tokens to Predict', min_value=-2, value=value, key="num_predict_input")
                    elif key == 'stop':
                        st.session_state.model_settings[key] = st.text_input('Stop Sequence', value=value, key="stop_input")
                    elif key == 'mirostat_mode':
                        st.session_state.model_settings[key] = st.selectbox('Mirostat Mode', [0, 1, 2], index=value, format_func=lambda x: f"Mode {x}", key="mirostat_mode_select")
                    elif key == 'seed':
                        st.session_state.model_settings[key] = st.number_input('Random Seed', min_value=0, value=value, key="seed_input")
                    elif key == 'system_prompt':
                        st.session_state.model_settings[key] = st.text_area('System Prompt:', value=value, height=100, key="system_prompt_input")

    csv_file = st.sidebar.file_uploader("📁 Choose a CSV file", type="csv")

    if csv_file is not None and st.session_state.df is None:
        st.session_state.df = load_csv(csv_file)

    if st.session_state.df is not None:
        df = st.session_state.df
        
        with st.sidebar.expander("🔢 Select Rows", expanded=False):
            start_row = st.number_input("Start Row", min_value=0, max_value=len(df)-1, value=0, key="start_row_input")
            end_row = st.number_input("End Row", min_value=start_row, max_value=len(df)-1, value=len(df)-1, key="end_row_input")

        new_column_name = st.sidebar.text_input("✏️ Name for the new column:", "Row Summary", key="new_column_name_input")
        
        headers = df.columns.tolist()
        dynamic_placeholder = "Summarize this: " + ", ".join([f"{header}: [@{header}]" for header in headers])
        
        if st.session_state.prompt_template == '':
            st.session_state.prompt_template = dynamic_placeholder

        # Define the label for the text area
        prompt_template_label = "🖋️ Enter prompt template:"

        # Create the text area in the sidebar
        prompt_template = st.sidebar.text_area(
            label=prompt_template_label,
            value=st.session_state.prompt_template,
            height=150,
            help="Use @column_name to reference column values. Type @ to see suggestions. Column names will be highlighted with brackets [].",
            key="prompt_template_input"
        )

        # Update session state when the text area changes
        if prompt_template != st.session_state.prompt_template:
            st.session_state.prompt_template = prompt_template

        # Define the autocomplete strategy for column names
        column_strategy = StrategyProps(
            id="columnName",
            match="\\B@(\\w*)$",
            search=f"async (term, callback) => {{const columns = {json.dumps(headers)}; callback(columns.filter(col => col.toLowerCase().startsWith(term.toLowerCase())));}}",
            replace="(column) => `[@${column}]`",
            template="(column) => column",
        )

        # Initialize the textcomplete component
        textcomplete(
            area_label=prompt_template_label,
            strategies=[column_strategy],
            max_count=5,
            on_select="(item) => {const textarea = document.querySelector('textarea[aria-label=\"🖋️ Enter prompt template:\"]'); const start = textarea.selectionStart; const end = textarea.selectionEnd; const text = textarea.value; const before = text.substring(0, start); const after = text.substring(end); textarea.value = before + item + after; textarea.selectionStart = textarea.selectionEnd = start + item.length; textarea.dispatchEvent(new Event('input', { bubbles: true }));}"
        )

        if st.sidebar.button('🚀 Process CSV'):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            preview_container = st.empty()
            stop_button_placeholder = st.empty()
            output_placeholder = st.empty()
        
            def process_csv(df, model, prompt_template, start_row, end_row, new_column_name, options):
                df[new_column_name] = ''
                total_rows = end_row - start_row + 1
                
                start_time = time.time()
                
                if options['seed'] != 0:
                    random.seed(options['seed'])
                
                for i in range(start_row, end_row + 1):
                    if stop_button_placeholder.button("⏹️ Stop Processing", key=f"stop_button_{i}"):
                        st.warning("Processing stopped by user.")
                        break
                    
                    row = df.iloc[i]
                    input_dict = {header: str(value) for header, value in row.items()}
                    try:
                        prompt = prompt_template
                        for header, value in input_dict.items():
                            prompt = prompt.replace(f"[@{header}]", value)
                        response = generate_output(st.session_state.ollama_url, model, prompt, options)
                        if response:
                            full_response = ""
                            for line in response.iter_lines():
                                if line:
                                    json_response = json.loads(line)
                                    if 'response' in json_response:
                                        full_response += json_response['response']
                                        df.at[i, new_column_name] = full_response
                                        
                                        preview_container.dataframe(df)
                                        output_placeholder.markdown(f"**Current cell prompt:**\n\n{html.escape(prompt)}\n\n**Current cell output:**\n\n{html.escape(full_response)}")
                                    
                                    if json_response.get('done', False):
                                        break
                        else:
                            df.at[i, new_column_name] = "Failed to generate output"
                    except KeyError as e:
                        st.error(f"Error in prompt template: {e}. Check your column references.")
                        break
                    except Exception as e:
                        st.error(f"Unexpected error: {e}")
                        break
                    
                    progress = (i - start_row + 1) / total_rows
                    progress_placeholder.progress(progress)
                    
                    elapsed_time = time.time() - start_time
                    estimated_total_time = elapsed_time / progress
                    remaining_time = estimated_total_time - elapsed_time
                    status_placeholder.text(f"⏳ Progress: {progress:.1%} | Time remaining: {format_time(remaining_time)}")
                
                return df

            # Prepare options dictionary
            options = st.session_state.model_settings.copy()
            if options['stop']:
                options['stop'] = [options['stop']]
            else:
                options['stop'] = None

            st.session_state.df = process_csv(df, model, prompt_template, start_row, end_row, new_column_name, options)
            st.session_state.processed_columns.append(new_column_name)
            
            progress_placeholder.empty()
            status_placeholder.empty()
            stop_button_placeholder.empty()
            output_placeholder.empty()
            
            st.success('✅ Processing complete!')
            
            csv_output = st.session_state.df.to_csv(index=False)
            st.download_button(
                label="📥 Download Results",
                data=csv_output,
                file_name="results.csv",
                mime="text/csv"
            )
        else:
            st.dataframe(st.session_state.df)
    else:
        st.sidebar.warning("Please upload a CSV file to begin.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; color: gray; font-size: 12px;'>Developed by Neo Mohsenvand, July 2024</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()