import dash
from dash import html, dcc, Input, Output, State, callback
import base64


dash.register_page(__name__, path='/')

layout = html.Div([
    html.H1("File Upload Example"),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '50%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px'
        },
        multiple=False
    ),
    html.Div(id='output-data')
])


@callback(Output('output-data', 'children'),
              [Input('upload-data', 'contents')],
              [State('upload-data', 'filename')])
def process_upload(contents, filename):
    if contents is not None:
        # Decode the file content
        decoded_content = base64.b64decode(contents.split(',')[1])
        filename = 'log_samples'
        # Save the file in the working directory
        with open(filename, 'wb') as file:
            file.write(decoded_content)

        return html.Div([
            html.H5(f'Successfully uploaded and saved file: {filename}')
        ])
