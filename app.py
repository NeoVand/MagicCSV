import streamlit as st
import pandas as pd
import requests
import json
import time
import random
from datetime import timedelta
import html

# Default Ollama URL
DEFAULT_OLLAMA_URL = 'http://localhost:11434'

def check_ollama_connection(ollama_url):
    try:
        requests.get(f'{ollama_url}/api/tags', timeout=5).raise_for_status()
        return True
    except requests.RequestException:
        return False

def get_ollama_models(ollama_url):
    try:
        response = requests.get(f'{ollama_url}/api/tags', timeout=5)
        response.raise_for_status()
        return [model['name'] for model in response.json()['models']]
    except requests.RequestException as e:
        st.sidebar.error(f"Error connecting to Ollama: {str(e)}")
        return []

def generate_output(ollama_url, model, prompt, temperature, system_prompt):
    try:
        data = {
            'model': model,
            'prompt': prompt,
            'temperature': temperature,
            'system': system_prompt
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

    st.sidebar.markdown("# 🔮 MagicCSV")

    if 'df' not in st.session_state:
        st.session_state.df = None

    if 'processed_columns' not in st.session_state:
        st.session_state.processed_columns = []

    if 'ollama_url' not in st.session_state:
        st.session_state.ollama_url = DEFAULT_OLLAMA_URL

    with st.sidebar.expander("🛠️ Model Settings", expanded=False):
        ollama_url = st.text_input("Ollama Server URL:", value=st.session_state.ollama_url)
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
                model = st.selectbox('Select Ollama Model:', models)
                temperature = st.slider('Temperature', min_value=0.0, max_value=2.0, value=0.7, step=0.1)
                system_prompt = st.text_area('System Prompt:', value='', height=100)
                seed = st.number_input('Seed (optional):', min_value=0, value=0, help="Set a seed for reproducible results. Leave as 0 for random seed.")

    csv_file = st.sidebar.file_uploader("📁 Choose a CSV file", type="csv")

    if csv_file is not None and st.session_state.df is None:
        st.session_state.df = load_csv(csv_file)

    if st.session_state.df is not None:
        df = st.session_state.df
        
        with st.sidebar.expander("🔢 Select Rows", expanded=False):
            start_row = st.number_input("Start Row", min_value=0, max_value=len(df)-1, value=0)
            end_row = st.number_input("End Row", min_value=start_row, max_value=len(df)-1, value=len(df)-1)

        new_column_name = st.sidebar.text_input("✏️ Name for the new column:", "Row Summary")
        
        headers = df.columns.tolist()
        dynamic_placeholder = "Summarize this: " + ", ".join([f"{header}: {{col{i+1}}}" for i, header in enumerate(headers)])
        
        column_names = [f"{{col{i+1}}}" for i in range(len(headers))]
        with st.sidebar.expander("📊 Available Column Placeholders", expanded=False):
            st.write(", ".join(column_names))

        prompt_template = st.sidebar.text_area('🖋️ Enter prompt template:', value=dynamic_placeholder)

        if st.sidebar.button('🚀 Process CSV'):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            preview_container = st.empty()
            stop_button_placeholder = st.empty()
            output_placeholder = st.empty()
        
            def process_csv(df, model, prompt_template, start_row, end_row, new_column_name, temperature, system_prompt, seed):
                df[new_column_name] = ''
                total_rows = end_row - start_row + 1
                
                start_time = time.time()
                
                if seed != 0:
                    random.seed(seed)
                
                for i in range(start_row, end_row + 1):
                    if stop_button_placeholder.button("⏹️ Stop Processing", key=f"stop_button_{i}"):
                        st.warning("Processing stopped by user.")
                        break
                    
                    row = df.iloc[i]
                    input_dict = {f"col{j+1}": str(value) for j, value in enumerate(row)}
                    try:
                        prompt = prompt_template.format(**input_dict)
                        response = generate_output(st.session_state.ollama_url, model, prompt, temperature, system_prompt)
                        if response:
                            full_response = ""
                            for line in response.iter_lines():
                                if line:
                                    json_response = json.loads(line)
                                    if 'response' in json_response:
                                        full_response += json_response['response']
                                        df.at[i, new_column_name] = full_response
                                        
                                        preview_container.dataframe(df)
                                        output_placeholder.markdown(f"**Current cell output:**\n\n{html.escape(full_response)}")
                                    
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

            st.session_state.df = process_csv(df, model, prompt_template, start_row, end_row, new_column_name, temperature, system_prompt, seed)
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