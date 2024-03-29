# -*- coding: utf-8 -*-
"""
Module doc string
"""
import pathlib
import re
from datetime import datetime
import flask
import dash
import dash_table
import matplotlib.colors as mcolors
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from precomputing import add_stopwords
from dash.dependencies import Output, Input, State
from dateutil import relativedelta
from wordcloud import WordCloud, STOPWORDS
from ldacomplaints import lda_analysis
from collections import deque
import datetime as dt
import random

# random.seed(42)
X = deque(maxlen=50)
Y = deque(maxlen=50)

DATA_PATH = pathlib.Path(__file__).parent.resolve()
EXTERNAL_STYLESHEETS = ["https://codepen.io/chriddyp/pen/bWLwgP.css"]
FILENAME = "data/movie_for_predict.csv"
PLOTLY_LOGO = "https://images.plot.ly/logo/new-branding/plotly-logomark.png"
GLOBAL_DF = pd.read_csv(DATA_PATH.joinpath(FILENAME), header=0)
# GLOBAL_DF = "Null"
PREDICTOR = "train/dataset/movie_metadata.csv"

"""
#  Somewhat helpful functions
"""


def get_complaint_count_by_company(dataframe, attribute):
    """ Count the frequency of key words under one specific attribute """
    company_counts = dataframe[attribute].value_counts()
    values = company_counts.keys().tolist()
    counts = company_counts.tolist()
    return values, counts


def get_value_by_attribute(GLOBAL_DF, attribute):
    col = GLOBAL_DF[attribute]
    col_list = col.tolist()
    return sorted(list(set(col_list)))


def predict(test_df, predictor_path):
    # TODO
    predictions = np.random.rand(10)
    predict_df = pd.DataFrame(data={"prediction":predictions})
    predict_df['movie title'] = test_df["movie title"]
    return predict_df


def make_options_bank_drop(values):
    """
    Helper function to generate the data format the dropdown dash component wants
    """
    ret = []
    for value in values:
        ret.append({"label": value, "value": value})
    return ret

def populate_lda_scatter(tsne_lda, lda_model, topic_num, df_dominant_topic):
    """Calculates LDA and returns figure data you can jam into a dcc.Graph()"""
    topic_top3words = [
        (i, topic)
        for i, topics in lda_model.show_topics(formatted=False)
        for j, (topic, wt) in enumerate(topics)
        if j < 3
    ]

    df_top3words_stacked = pd.DataFrame(topic_top3words, columns=["topic_id", "words"])
    df_top3words = df_top3words_stacked.groupby("topic_id").agg(", \n".join)
    df_top3words.reset_index(level=0, inplace=True)

    tsne_df = pd.DataFrame(
        {
            "tsne_x": tsne_lda[:, 0],
            "tsne_y": tsne_lda[:, 1],
            "topic_num": topic_num,
            "doc_num": df_dominant_topic["Document_No"],
        }
    )
    mycolors = np.array([color for name, color in mcolors.TABLEAU_COLORS.items()])

    # Plot and embed in ipython notebook!
    # for each topic create separate trace
    traces = []
    for topic_id in df_top3words["topic_id"]:
        # print('Topic: {} \nWords: {}'.format(idx, topic))
        tsne_df_f = tsne_df[tsne_df.topic_num == topic_id]
        cluster_name = ", ".join(
            df_top3words[df_top3words["topic_id"] == topic_id]["words"].to_list()
        )
        trace = go.Scatter(
            name=cluster_name,
            x=tsne_df_f["tsne_x"],
            y=tsne_df_f["tsne_y"],
            mode="markers",
            hovertext=tsne_df_f["doc_num"],
            marker=dict(
                size=6,
                color=mycolors[tsne_df_f["topic_num"]],  # set color equal to a variable
                colorscale="Viridis",
                showscale=False,
            ),
        )
        traces.append(trace)

    layout = go.Layout({"title": "Topic analysis using LDA"})

    return {"data": traces, "layout": layout}


def plotly_wordcloud(data_frame):
    """A wonderful function that returns figure data for three equally
    wonderful plots: wordcloud, frequency histogram and treemap"""
    complaints_text = list(data_frame[0].dropna().values)
    ## join all documents in corpus
    text = " ".join(list(complaints_text))
    STOPWORDS.add("movie")
    STOPWORDS.add("film")

    word_cloud = WordCloud(stopwords=set(STOPWORDS), max_words=100, max_font_size=90)
    word_cloud.generate(text)

    word_list = []
    freq_list = []
    fontsize_list = []
    position_list = []
    orientation_list = []
    color_list = []

    for (word, freq), fontsize, position, orientation, color in word_cloud.layout_:
        word_list.append(word)
        freq_list.append(freq)
        fontsize_list.append(fontsize)
        position_list.append(position)
        orientation_list.append(orientation)
        color_list.append(color)

    # get the positions
    x_arr = []
    y_arr = []
    for i in position_list:
        x_arr.append(i[0])
        y_arr.append(i[1])

    # get the relative occurence frequencies
    new_freq_list = []
    for i in freq_list:
        new_freq_list.append(i * 80)

    trace = go.Scatter(
        x=x_arr,
        y=y_arr,
        textfont=dict(size=new_freq_list, color=color_list),
        hoverinfo="text",
        textposition="top center",
        hovertext=["{0} - {1}".format(w, f) for w, f in zip(word_list, freq_list)],
        mode="text",
        text=word_list,
    )

    layout = go.Layout(
        {
            "xaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 250],
            },
            "yaxis": {
                "showgrid": False,
                "showticklabels": False,
                "zeroline": False,
                "automargin": True,
                "range": [-100, 450],
            },
            "margin": dict(t=20, b=20, l=10, r=10, pad=4),
            "hovermode": "closest",
        }
    )

    wordcloud_figure_data = {"data": [trace], "layout": layout}
    word_list_top = word_list[:25]
    word_list_top.reverse()
    freq_list_top = freq_list[:25]
    freq_list_top.reverse()

    frequency_figure_data = {
        "data": [
            {
                "y": word_list_top,
                "x": freq_list_top,
                "type": "bar",
                "name": "",
                "orientation": "h",
            }
        ],
        "layout": {"height": "550", "margin": dict(t=20, b=20, l=100, r=20, pad=4)},
    }
    treemap_trace = go.Treemap(
        labels=word_list_top, parents=[""] * len(word_list_top), values=freq_list_top
    )
    treemap_layout = go.Layout({"margin": dict(t=10, b=10, l=5, r=5, pad=4)})
    treemap_figure = {"data": [treemap_trace], "layout": treemap_layout}
    return wordcloud_figure_data, frequency_figure_data, treemap_figure


MOVIES_NAMES = get_value_by_attribute(GLOBAL_DF, "movie title")
MOVIES_DROPDOWN = make_options_bank_drop(MOVIES_NAMES)

"""
#  Page layout and contents

In an effort to clean up the code a bit, we decided to break it apart into
sections. For instance: LEFT_COLUMN is the input controls you see in that gray
box on the top left. The body variable is the overall structure which most other
sections go into. This just makes it ever so slightly easier to find the right 
spot to add to or change without having to count too many brackets.
"""

NAVBAR = dbc.Navbar(
    children=[
        html.A(
            # Use row and col to control vertical alignment of logo / brand
            dbc.Row(
                [
                    dbc.Col(html.Img(src=PLOTLY_LOGO, height="30px")),
                    dbc.Col(
                        dbc.NavbarBrand(
                            "USA Box Office Predictor", className="ml-2")
                    ),
                ],
                align="center",
                no_gutters=True,
            ),
            href="https://github.com/ZavierLyu/box-office-predictor",
        )
    ],
    color="dark",
    dark=True,
    sticky="top",
)


TOP_BANKS_PLOT = [
    dbc.CardHeader(html.H5("Box Office Predicting Result")),
    dbc.CardBody(
        [
            dcc.Graph(id="bank-sample"),
            dcc.Interval(
                id='predict-update',
                interval=2*1000,  # in milliseconds
            )
        ]
    ),
]

LEFT_COLUMN = dbc.Jumbotron(
    [
        html.H4(children="Select Coming Movies", className="display-5"),
        html.Hr(className="my-2"),

        html.Label("Select a movie", style={
                   "marginTop": 50}, className="lead"),
        html.P(
            "(You can use the dropdown or click the barchart on the right)",
            style={"fontSize": 10, "font-weight": "lighter"},
        ),
        dcc.Dropdown(
            id="bank-drop", clearable=False, style={"marginBottom": 50, "font-size": 12},
            options=MOVIES_DROPDOWN, value=MOVIES_NAMES[0]
        )
    ]
)

WORDCLOUD_PLOTS = [
    dbc.CardHeader(html.H5("Most frequently used words in comments")),
    dbc.CardBody(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Loading(
                            id="loading-frequencies",
                            children=[dcc.Graph(id="frequency_figure")],
                            type="default",
                        )
                    ),
                    dbc.Col(
                        [
                            dcc.Tabs(
                                id="tabs",
                                children=[
                                    dcc.Tab(
                                        label="Treemap",
                                        children=[
                                            dcc.Loading(
                                                id="loading-treemap",
                                                children=[dcc.Graph(id="bank-treemap")],
                                                type="default",
                                            )
                                        ],
                                    ),
                                    dcc.Tab(
                                        label="Wordcloud",
                                        children=[
                                            dcc.Loading(
                                                id="loading-wordcloud",
                                                children=[
                                                    dcc.Graph(id="bank-wordcloud")
                                                ],
                                                type="default",
                                            )
                                        ],
                                    ),
                                ],
                            )
                        ],
                        md=8,
                    ),
                ]
            )
        ]
    ),
]

BODY = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(LEFT_COLUMN, md=4, align="center"),
                dbc.Col(dbc.Card(TOP_BANKS_PLOT), md=8),
            ],
            style={"marginTop": 30},
        ),
        dbc.Card(WORDCLOUD_PLOTS)
    ],
    className="mt-12",
)

SERVER = flask.Flask(__name__)
APP = dash.Dash(__name__, external_stylesheets=[
                dbc.themes.BOOTSTRAP], server=SERVER)
APP.layout = html.Div(children=[NAVBAR, BODY])

"""
#  Callbacks
"""

'''
For live predictions
'''
@APP.callback(
    Output("bank-sample", "figure"),
    [Input("bank-drop", "value"), Input("predict-update", "n_intervals")],
)
def update_bank_sample_plot(movie_name, intervals):
    """ TODO """
    print("redrawing bank-sample...")
    prediction_df = predict(GLOBAL_DF, " ")
    prediction = prediction_df[prediction_df["movie title"]==movie_name].iloc[0,0]
    # print(prediction)
    # X = deque(maxlen=20)
    X.append(str(dt.datetime.now()))
    Y.append(np.round(prediction + random.randint(-2,2), 1))

    data = [
        go.Scatter(
            x=list(X),
            y=list(Y),
            name='Scatter',
            mode= 'lines+markers'
        )
    ]
    layout = {
        "autosize": True,
        # "margin": dict(t=8, b=8, l=35, r=0, pad=4),
        "xaxis": {"showticklabels": True},
        "title": 'Live Box Office for: "{}" is {}$'.format(movie_name, Y[-1])
    }
    print("redrawing bank-sample...done")
    return {"data": data, "layout": layout}


'''
For WordCloud
'''

@APP.callback(
    [
        Output("bank-wordcloud", "figure"),
        Output("frequency_figure", "figure"),
        Output("bank-treemap", "figure"),
    ],
    [
        Input("bank-drop", "value"),
    ]
)

def update_wordcloud_plot(value_drop):
    """ TODO"""
    print("draw workcloud")
    local_df = pd.read_csv("comment_csv/{}.csv".format(value_drop), header=None)
    wordcloud, frequency_figure, treemap = plotly_wordcloud(local_df)
    # print(local_df.head())
    print("redrawing bank-wordcloud...done")
    return (wordcloud, frequency_figure, treemap)

if __name__ == "__main__":
    APP.run_server(debug=True)
