from dash import html, dcc
import dash_daq as daq                            

def get_sonar_section(id):
    return html.Div([
            html.Div([
                html.Label("SONAR", style={'marginRight': '10px', 'alignSelf': 'center'}),
                daq.ToggleSwitch(id='sonar-toggle', value=False)
            ], style={'display': 'flex', 'alignItems': 'center'}),
            html.Div(id='sonar-section-container'),

            dcc.Store(id='area-id-store', data=id),

            html.Div(id='sonar-explanation-controls', children=[
                dcc.RadioItems(
                    id='explanation-mode-selector',
                    options=[
                        {'label': 'Counterfactual', 'value': 0},
                        {'label': 'Prototype', 'value': 1},
                        {'label': 'Both', 'value': 2}
                    ],
                    value=0,
                    labelStyle={'display': 'inline-block', 'marginRight': '15px'},
                    style={'marginTop': '10px'}
                ),
                html.Div([
                    dcc.Loading(
                        id="loading-explanation",
                        type="circle",
                        children=html.Div(id='explanation-container'),
                        fullscreen=False
                    )
                ], style={'marginTop': '20px'})
            ], style={'display': 'none'})
        ], style={'marginTop': '20px'})
