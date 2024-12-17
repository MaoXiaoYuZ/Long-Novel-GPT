import sys
import os
import yaml
import gradio as gr
from itertools import chain
import pickle

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.writer import Writer
from llm_api import ModelConfig

ak, sk = '', ''
model = ModelConfig(model='ERNIE-4.0-8K', ak=ak, sk=sk, max_tokens=4000)
sub_model = ModelConfig(model='ERNIE-3.5-8K', ak=ak, sk=sk, max_tokens=4000)

writer = None

PICKLE_FILE = 'writer_state.pkl'

def save_writer():
    global writer
    if writer is not None:
        with open(PICKLE_FILE, 'wb') as f:
            pickle.dump(writer, f)
        return "Writer saved to pickle file"
    else:
        return "No Writer instance to save"
    

def load_writer():
    global writer
    if os.path.exists(PICKLE_FILE):
        with open(PICKLE_FILE, 'rb') as f:
            writer = pickle.load(f)
        return "Writer loaded from pickle file"
    else:
        return "No Writer instance to load"

if os.path.exists(PICKLE_FILE):
    load_writer()
    if writer is not None:
        writer.batch_map(prompt="", y_span=(0, len(writer.y)), chunk_length=1000, context_length=0, smooth=True)
else:
    print("No writer state file found. Please initialize writer first.")

def initialize_writer(plot, text):
    global writer
    if os.path.exists(PICKLE_FILE):
        load_writer()
        return "Writer loaded from pickle file"
    else:
        writer = Writer(x=plot, y=text, model=model, sub_model=sub_model)
        return "New Writer initialized"
    
def test_update_map(plot, text):
    global writer
    if writer is None:
        return "Please initialize the writer first."
    
    writer.x = plot
    writer.y = text

    # Execute update_map
    for output in writer.update_map():
        yield output['response_msgs'].response
    
    # Generate output string
    output = ""
    dash_count = 20
    output += f"\n{'-' * dash_count}xy_pairs{'-' * dash_count}\n"
    for i, (plot_chunk, text_chunk) in enumerate(writer.xy_pairs, 1):
        output += f"{'-' * dash_count}pair {i}{'-' * dash_count}\n"
        output += f"x: {plot_chunk}\n"
        output += f"y: {text_chunk}\n"
    output += f"{'-' * (dash_count * 2 + 8)}\n"

    yield output
    
    return output

def run_gradio_interface():
    # Load examples from YAML file
    with open('prompts/text-plot-examples.yaml', 'r', encoding='utf-8') as file:
        examples_data = yaml.safe_load(file)
    
    # Get the first example
    first_example = examples_data['examples'][0]
    plot = first_example['plot']
    text = first_example['text']

    # Define Gradio blocks
    with gr.Blocks(title="Writer Test Interface") as demo:
        gr.Markdown("# Writer Test Interface")
        gr.Markdown("Test the Writer's update_map function with the first example.")
        
        with gr.Row():
            plot_input = gr.Textbox(label="X (Plot)", value=plot, lines=20)
            text_input = gr.Textbox(label="Y (Text)", value=text, lines=20)
        
        with gr.Row():
            init_button = gr.Button("Initialize Writer")
            test_button = gr.Button("Test update_map")
            save_button = gr.Button("Save Writer")
        
        output = gr.Textbox(label="Output")
        
        init_button.click(fn=initialize_writer, inputs=[plot_input, text_input], outputs=output)
        test_button.click(fn=test_update_map, inputs=[plot_input, text_input], outputs=output)
        save_button.click(fn=save_writer, inputs=[], outputs=output)

    demo.launch()

if __name__ == "__main__":
    run_gradio_interface()
