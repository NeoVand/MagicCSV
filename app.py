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
                
                # Advanced Model Settings
                st.markdown("### Advanced Model Settings")
                
                temperature = st.slider('Temperature', min_value=0.0, max_value=2.0, value=0.8, step=0.1,
                                        help="Controls randomness. Lower values make the model more deterministic, higher values make it more creative.")
                
                top_p = st.slider('Top P', min_value=0.0, max_value=1.0, value=0.9, step=0.05,
                                  help="Nucleus sampling. A higher value considers more lower-probability tokens.")
                
                top_k = st.slider('Top K', min_value=1, max_value=100, value=40,
                                  help="Limits the next token selection to the K most probable tokens.")
                
                min_p = st.slider('Min P', min_value=0.0, max_value=1.0, value=0.05, step=0.01,
                                  help="Sets a minimum probability threshold for token selection.")
                
                repeat_penalty = st.slider('Repeat Penalty', min_value=0.0, max_value=2.0, value=1.1, step=0.1,
                                           help="Penalizes repeated tokens. Higher values reduce repetition.")
                
                repeat_last_n = st.slider('Repeat Last N', min_value=0, max_value=2048, value=64,
                                          help="Number of tokens to look back for repetitions.")
                
                num_predict = st.number_input('Number of Tokens to Predict', min_value=-2, value=128,
                                              help="-1 for infinite generation, -2 to fill context window")
                
                stop = st.text_input('Stop Sequence', value='',
                                     help="The model will stop generating when it encounters this sequence.")
                
                tfs_z = st.slider('TFS Z', min_value=0.0, max_value=3.0, value=1.0, step=0.1,
                                  help="Tail free sampling parameter. Higher values reduce low-probability tokens more.")
                
                mirostat_mode = st.selectbox('Mirostat Mode', [0, 1, 2], format_func=lambda x: f"Mode {x}",
                                             help="Mirostat sampling mode. 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0")
                
                mirostat_tau = st.slider('Mirostat Tau', min_value=0.0, max_value=10.0, value=5.0, step=0.1,
                                         help="Mirostat target entropy. Lower values lead to more focused output.")
                
                mirostat_eta = st.slider('Mirostat Eta', min_value=0.0, max_value=1.0, value=0.1, step=0.01,
                                         help="Mirostat learning rate. Higher values make adjustments more quickly.")
                
                num_ctx = st.slider('Context Window Size', min_value=512, max_value=8192, value=2048, step=512,
                                    help="Size of the context window for token generation.")
                
                seed = st.number_input('Random Seed', min_value=0, value=42,
                                       help="Set a seed for reproducible outputs. 0 for random seed.")

                system_prompt = st.text_area('System Prompt:', value='', height=100,
                                             help="Sets the behavior of the AI assistant.")

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
        
        prompt_template = st.sidebar.text_area(
            '🖋️ Enter prompt template:',
            value=dynamic_placeholder,
            height=150,
            help="Use {col1}, {col2}, etc. as placeholders for column values."
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
                    input_dict = {f"col{j+1}": str(value) for j, value in enumerate(row)}
                    try:
                        prompt = prompt_template.format(**input_dict)
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
            options = {
                'temperature': temperature,
                'top_p': top_p,
                'top_k': top_k,
                'min_p': min_p,
                'repeat_penalty': repeat_penalty,
                'repeat_last_n': repeat_last_n,
                'num_predict': num_predict,
                'stop': [stop] if stop else None,
                'tfs_z': tfs_z,
                'mirostat': mirostat_mode,
                'mirostat_tau': mirostat_tau,
                'mirostat_eta': mirostat_eta,
                'num_ctx': num_ctx,
                'seed': seed
            }
            
            # Add system prompt if provided
            if system_prompt:
                options['system'] = system_prompt

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