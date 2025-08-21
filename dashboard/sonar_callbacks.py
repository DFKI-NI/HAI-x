from dash import dcc, html, Input, Output, State
import requests
import os
import random
import logging

def register_sonar_callbacks(app):
    """Register callbacks for the SONAR section of the dashboard."""
    
    @app.callback(
        Output('sonar-section-container', 'children'),
        Output('sonar-explanation-controls', 'style'),
        Input('sonar-toggle', 'value')
    )
    def toggle_sonar_section(show):
        if show:
            return (
                html.Div([
                    load_sonar_detections(),
                    build_chatbox()
                ]),
                {'display': 'block'}
            )
        return '', {'display': 'none'}

    @app.callback(
        Output('explanation-container', 'children'),
        Input('chat-send', 'n_clicks'),
        State('chat-input', 'value'),
        State('area-id-store', 'data'),
        State('explanation-mode-selector', 'value'),
        prevent_initial_call=True
    )
    def show_explanation_on_send(n_clicks, chat_text, area_id, mode):
        if n_clicks and chat_text and chat_text.strip():
            return load_cf_proto_explanation(prompt=chat_text, mode=mode)
        return ''


    def load_sonar_detections():
        """ Loading Detections from the SONAR Sensor"""
        sonar_img = "static/img/sonar/detections/can.png"
        class_name = sonar_img.split('/')[-1].replace('.png', '').capitalize()
        return html.Div([
            html.H5("SONAR Detections"),
            html.Img(src=sonar_img, style={'maxWidth': '100%', 'margin': '5px'}),
            html.P([
                html.Strong("Class: "),
                class_name
            ], style={'margin': '5px 0 0 5px', 'fontStyle': 'italic'})
        ], style={'marginTop': '20px'})

    # TODO: Check the pattern matching IDs for scalability: https://dash.plotly.com/pattern-matching-callbacks
    # Reasoning / Explanation helper functions:
    def build_chatbox():
        return html.Div([
            html.H5("Having some thoughts?"),
            dcc.Textarea(id='chat-input', placeholder='What do you think ...', style={
                'width': '100%', 'height': 60
            }),
            html.Button('send', id='chat-send', n_clicks=0)
        ], style={'marginTop': '20px'})


    def load_cf_proto_explanation(prompt, mode=2):
        """Fetch counterfactual and prototype images from FastAPI and render them.
        Args:
            prompt (str): The user prompt for the explanation.
            mode (int): 0: Counterfactual, 1: Prototype, 2: Both.
        """
        def similarity_indicator(score):
            if score >= 0.85:
                color = "green"
            elif score >= 0.45:
                color = "orange"
            else:
                color = "red"
            
            circle = html.Span(style={
                'display': 'inline-block',
                'width': '12px',
                'height': '12px',
                'borderRadius': '50%',
                'backgroundColor': color,
                'marginRight': '8px'
            })

            label = html.Span(f"SSIM: {int(score * 100)}% similar", style={'fontWeight': 'bold'})

            return html.Div([circle, label], style={'display': 'flex', 'alignItems': 'center', 'marginTop': '5px'})
          

        def fetch_results(single_mode, prompt="default prompt", target_class="can", selected_file=None):
            det_dir = "static/img/sonar/detections"
            rgb_dir = "static/img/sonar/rgb"
            proto_dir = "static/img/sonar/sonar_prototypes"

            if selected_file is None:
                det_files = [f for f in os.listdir(det_dir) if f.endswith(".png")]
                if not det_files:
                    raise FileNotFoundError("No detection images found.")
                # selected_file = random.choice(det_files)
                # FIXME: selected file is fixed to can.png for now
                selected_file = "can.png"

            base_name = os.path.splitext(selected_file)[0]

            files = {}
            try:
                files['image'] = open(os.path.join(det_dir, selected_file), 'rb')

                if single_mode == 1:
                    rgb_path = os.path.join(rgb_dir, f"{base_name}.png")
                    proto_path = os.path.join(proto_dir, f"{target_class}.png")

                    if os.path.exists(rgb_path):
                        files['rgb_image'] = open(rgb_path, 'rb')
                    else:
                        raise FileNotFoundError(f"RGB image not found: {rgb_path}")

                    if os.path.exists(proto_path):
                        files['prototype_image'] = open(proto_path, 'rb')
                    else:
                        raise FileNotFoundError(f"Prototype image not found: {proto_path}")

                data = {
                    'gps': "0,0",
                    'prompt': prompt,
                    'target_class': target_class,
                    'mode': single_mode
                }

                response = requests.post("http://localhost:8000/generate", files=files, data=data)
                response.raise_for_status()
                return response.json()

            finally:
                for f in files.values():
                    f.close()

        try:
                if mode not in {0, 1, 2}:
                    raise ValueError(f"Invalid mode: {mode}. Must be 0 (CF), 1 (Proto), or 2 (Both).")
                
                det_dir = "static/img/sonar/detections"
                det_files = [f for f in os.listdir(det_dir) if f.endswith(".png")]
                if not det_files:
                    raise FileNotFoundError("No detection images found.")
                selected_file = random.choice(det_files)
                base_name = os.path.splitext(selected_file)[0]

                children = [html.H5("Counterfactual and Prototype-based Explanations")]
                blocks = []
                children = [html.H5("Counterfactual and Prototype-based Explanations")]
                blocks = []

                if mode in {0, 2}:  # Counterfactual or Both
                    cf_results = fetch_results(0, prompt=prompt, target_class="can", selected_file=selected_file)

                    cf_img_url = cf_results.get("cf_generated_image")
                    cf_abs_diff_url = cf_results.get("cf_abs_diff")
                    cf_log_url = cf_results.get("cf_log")
                    cf_ssim_score = 0.0

                    if cf_log_url:
                        log_resp = requests.get(cf_log_url)
                        log_resp.raise_for_status()
                        cf_ssim_score = log_resp.json().get('ssim_score', 0.0)

                    if cf_img_url:
                        blocks.append(html.Div([
                            html.H6("Counterfactual:"),
                            html.Img(src=cf_img_url, style={'maxWidth': '100%', 'margin': '5px'}),
                            html.Img(src=cf_abs_diff_url, style={'maxWidth': '100%', 'margin': '5px'}),
                            similarity_indicator(cf_ssim_score)
                        ], style={'marginRight': '20px', 'maxWidth': '45%'}))

                if mode in {1, 2}:  # Prototype or Both
                    proto_results = fetch_results(1, prompt=prompt, target_class="can", selected_file=selected_file)
                    proto_input_image_url = proto_results.get("proto_input_image")
                    proto_input_bg_removed_url = proto_results.get("proto_input_bg_removed")
                    proto_input_processed_url = proto_results.get("proto_input_processed")
                    proto_generated_image_url = proto_results.get("proto_generated_image")
                    sonar_target_image_url = proto_results.get("sonar_target_image")

                    if proto_generated_image_url:
                        blocks.append(html.Div([
                            html.H6("Prototype"),

                            html.Div([
                                html.Div([
                                    html.P("Sonar Target"),
                                    html.Img(src=sonar_target_image_url, style={'width': '100%', 'marginBottom': '10px'}),
                                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

                                html.Div([
                                    html.P("Generated Prototype"),
                                    html.Img(src=proto_generated_image_url, style={'width': '100%', 'marginBottom': '10px'}),
                                ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                            ]),

                            html.Div([
                                html.Div([
                                    html.P("Background Removed"),
                                    html.Img(src=proto_input_bg_removed_url, style={'width': '100%', 'marginBottom': '10px'}),
                                ], style={'width': '32%', 'display': 'inline-block', 'marginRight': '1%', 'verticalAlign': 'top'}),

                                html.Div([
                                    html.P("CLAHE Processed"),
                                    html.Img(src=proto_input_processed_url, style={'width': '100%', 'marginBottom': '10px'}),
                                ], style={'width': '32%', 'display': 'inline-block', 'marginRight': '1%', 'verticalAlign': 'top'}),

                                html.Div([
                                    html.P("Original Input"),
                                    html.Img(src=proto_input_image_url, style={'width': '100%', 'marginBottom': '10px'}),
                                ], style={'width': '32%', 'display': 'inline-block', 'verticalAlign': 'top'}),
                            ])
                        ], style={'maxWidth': '100%', 'marginTop': '10px'}))

                children.append(html.Div(blocks, style={'display': 'flex', 'flexWrap': 'wrap', 'justifyContent': 'space-between'}))
                return html.Div(children, style={'marginTop': '20px'})

        except Exception as e:
            return html.Div(f"Error loading explanations: {str(e)}", style={'color': 'red'})