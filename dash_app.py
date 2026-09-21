import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, State, dash_table, callback
import dash_bootstrap_components as dbc

# --- Carga datos ---
DATA_PATH = Path(__file__).parent / "data" / "gapminder.csv"
try:
    df = pd.read_csv(DATA_PATH)
except Exception as e:
    print(f"[WARN] no se pudo leer {DATA_PATH}: {e}, intentando URL remota")
    df = pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv")

NAME_FIX = {
    "Congo, Dem. Rep.": "Democratic Republic of Congo",
    "Congo, Rep.": "Republic of Congo",
    "Cote d'Ivoire": "Ivory Coast",
}
df["country_display"] = df["country"].replace(NAME_FIX)

year_min = int(df["year"].min())
year_max = int(df["year"].max())
continents = sorted(df["continent"].unique())
countries = sorted(df["country"].unique())

CONTINENT_COLORS = {
    "Asia": "#636EFA",
    "Europe": "#00CC96",
    "Africa": "#EF553B",
    "Americas": "#AB63FA",
    "Oceania": "#FFA15A",
    "FSU": "#19D3F3",
}

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=False,
    title="Gapminder World",
)
server = app.server

def filter_df(year_rng, conts, cntrs):
    d = df[(df["year"] >= year_rng[0]) & (df["year"] <= year_rng[1])]
    if conts:
        d = d[d["continent"].isin(conts)]
    if cntrs:
        d = d[d["country"].isin(cntrs)]
    return d

# --- Layout ESTÁTICO (todos los Graphs existen desde el inicio) ---
app.layout = dbc.Container(
    [
        dcc.Store(id="anim_year", data=year_min),
        dcc.Store(id="is_playing", data=False),
        dcc.Interval(id="play_interval", interval=900, n_intervals=0, disabled=True),
        html.H1(
            [
                html.I(className="fas fa-globe-americas me-2"),
                "Gapminder World",
                html.Span("  ·  vida, población y renta 1952-2007", style={"fontSize": "15px", "fontWeight": "400", "color": "#6c757d", "marginLeft": "10px"}),
            ],
            className="my-3",
            style={"fontFamily": "Inter, system-ui, sans-serif", "fontWeight": "700", "letterSpacing": "-0.02em"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.Label("Rango de años", className="fw-semibold mb-1"),
                            dcc.RangeSlider(id="year_range", min=year_min, max=year_max, value=[year_min, year_max], marks={y: str(y) for y in range(year_min, year_max + 1, 10)}, step=1, tooltip={"placement": "bottom", "always_visible": False}),
                            html.Div([dbc.Button([html.I(className="fas fa-play me-1"), "Play"], id="play_btn", color="primary", size="sm", className="me-2"), dbc.Button([html.I(className="fas fa-pause me-1"), "Pause"], id="pause_btn", color="secondary", outline=True, size="sm", disabled=True)], className="d-flex mt-2"),
                            html.Hr(className="my-3"),
                            html.Label("Continente", className="fw-semibold mb-1"),
                            dbc.Checklist(id="continent_filter", options=[{"label": c, "value": c} for c in continents], value=continents, inline=False),
                            html.Hr(className="my-3"),
                            html.Label("Países (opcional)", className="fw-semibold mb-1"),
                            dcc.Dropdown(id="country_filter", options=[{"label": c, "value": c} for c in countries], value=[], multi=True, placeholder="Todos los países", searchable=True),
                            html.Hr(className="my-3"),
                            dbc.Button([html.I(className="fas fa-undo me-1"), "Reset filtros"], id="reset_btn", color="secondary", outline=True, className="w-100"),
                            html.Div(html.Small("Dataset: gapminder_unfiltered.csv · 3.314 filas. Tema claro, Inter.", className="text-muted"), className="mt-3"),
                        ],
                        className="p-3 bg-light border rounded",
                        style={"position": "sticky", "top": "16px"},
                    ),
                    width=3,
                ),
                dbc.Col(
                    [
                        dbc.Row(
                            [
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div([html.I(className="fas fa-flag me-2"), html.Span("Países", className="text-muted small")]), html.H3(id="kpi_countries", className="mb-0 mt-1"), html.Small("distintos", className="text-muted")]), className="h-100 border-0 shadow-sm"), width=3),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div([html.I(className="fas fa-users me-2"), html.Span("Población total", className="text-muted small")]), html.H3(id="kpi_pop", className="mb-0 mt-1"), html.Small(id="kpi_pop_sub", className="text-muted")]), className="h-100 border-0 shadow-sm"), width=3),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div([html.I(className="fas fa-heart me-2"), html.Span("Vida promedio", className="text-muted small")]), html.H3(id="kpi_life", className="mb-0 mt-1"), html.Small("años", className="text-muted")]), className="h-100 border-0 shadow-sm"), width=3),
                                dbc.Col(dbc.Card(dbc.CardBody([html.Div([html.I(className="fas fa-dollar-sign me-2"), html.Span("PIB per cápita", className="text-muted small")]), html.H3(id="kpi_gdp", className="mb-0 mt-1"), html.Small("mediana · USD", className="text-muted")]), className="h-100 border-0 shadow-sm"), width=3),
                            ],
                            className="mb-3 g-2",
                        ),
                        dcc.Tabs(
                            id="tabs",
                            value="tab-overview",
                            children=[
                                dcc.Tab(
                                    label="Overview",
                                    value="tab-overview",
                                    children=html.Div(
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Card(
                                                        [
                                                            dbc.CardHeader(
                                                                [
                                                                    "PIB per cápita vs Esperanza de vida",
                                                                    dbc.Button(html.I(className="fas fa-ellipsis-v"), id="open_popover_bubble", color="link", size="sm", className="float-end py-0"),
                                                                    dbc.Popover([dbc.PopoverHeader("Color por"), dbc.PopoverBody(dbc.RadioItems(id="bubble_color", options=[{"label": c, "value": c} for c in ["continent", "country"]], value="continent", inline=False))], target="open_popover_bubble", trigger="click", placement="top"),
                                                                ]
                                                            ),
                                                            dbc.CardBody(dcc.Graph(id="bubble", config={"displayModeBar": False})),
                                                        ],
                                                        className="h-100",
                                                    ),
                                                    width=8,
                                                ),
                                                dbc.Col(dbc.Card([dbc.CardHeader("Promedio por continente"), dbc.CardBody(dcc.Graph(id="bar", config={"displayModeBar": False}))], className="h-100"), width=4),
                                            ],
                                            className="g-3",
                                        ),
                                        className="p-3",
                                    ),
                                ),
                                dcc.Tab(
                                    label="Tendencias",
                                    value="tab-tendencias",
                                    children=html.Div(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(dbc.Row([dbc.Col(html.Span("Evolución temporal"), width="auto", className="d-flex align-items-center fw-semibold"), dbc.Col(dbc.RadioItems(id="line_metric", options=[{"label": "Vida", "value": "lifeExp"}, {"label": "PIB pc", "value": "gdpPercap"}, {"label": "Población", "value": "pop"}], value="lifeExp", inline=True, className="float-end"), width="auto")], justify="between", align="center")),
                                                dbc.CardBody(dcc.Graph(id="line", config={"displayModeBar": False})),
                                            ]
                                        ),
                                        className="p-3",
                                    ),
                                ),
                                dcc.Tab(
                                    label="Mapa",
                                    value="tab-mapa",
                                    children=html.Div(
                                        dbc.Card(
                                            [
                                                dbc.CardHeader(dbc.Row([dbc.Col(html.Span("Mapa coroplético"), width="auto", className="d-flex align-items-center fw-semibold"), dbc.Col(dbc.RadioItems(id="map_metric", options=[{"label": "Vida", "value": "lifeExp"}, {"label": "PIB pc", "value": "gdpPercap"}], value="lifeExp", inline=True, className="float-end"), width="auto")], justify="between", align="center")),
                                                dbc.CardBody(dcc.Graph(id="choropleth", config={"displayModeBar": False}, style={"height": "520px"})),
                                                dbc.CardFooter(html.Small("Blues clara · agregación promedio del rango por país", className="text-muted")),
                                            ]
                                        ),
                                        className="p-3",
                                    ),
                                ),
                                dcc.Tab(
                                    label="Datos",
                                    value="tab-datos",
                                    children=html.Div(
                                        dbc.Card([dbc.CardHeader(dbc.Row([dbc.Col("Datos filtrados", width="auto", className="fw-semibold"), dbc.Col(html.Small(id="table_count", className="text-muted"), width="auto")], justify="between", align="center")), dbc.CardBody(html.Div(id="table_container", style={"maxHeight": "520px", "overflowY": "auto"}))]),
                                        className="p-3",
                                    ),
                                ),
                            ],
                        ),
                    ],
                    width=9,
                ),
            ]
        ),
    ],
    fluid=True,
    style={"backgroundColor": "#f8f9fa", "minHeight": "100vh", "paddingBottom": "24px", "fontFamily": "Inter, system-ui, sans-serif"},
)

# --- Callback principal (ahora todos los Input existen siempre) ---
@callback(
    Output("kpi_countries", "children"),
    Output("kpi_pop", "children"),
    Output("kpi_pop_sub", "children"),
    Output("kpi_life", "children"),
    Output("kpi_gdp", "children"),
    Output("table_count", "children"),
    Output("table_container", "children"),
    Output("bubble", "figure"),
    Output("bar", "figure"),
    Output("line", "figure"),
    Output("choropleth", "figure"),
    Input("year_range", "value"),
    Input("continent_filter", "value"),
    Input("country_filter", "value"),
    Input("bubble_color", "value"),
    Input("line_metric", "value"),
    Input("map_metric", "value"),
)
def update_all(year_rng, conts, cntrs, bubble_color, line_metric, map_metric):
    if bubble_color is None:
        bubble_color = "continent"
    if line_metric is None:
        line_metric = "lifeExp"
    if map_metric is None:
        map_metric = "lifeExp"
    if not year_rng or len(year_rng) != 2:
        year_rng = [year_min, year_max]
    if conts is None:
        conts = continents
    d = filter_df(year_rng, conts, cntrs)
    n_countries = d["country"].nunique() if not d.empty else 0
    total_pop = d["pop"].sum() if not d.empty else 0
    avg_life = d["lifeExp"].mean() if not d.empty else 0
    med_gdp = d["gdpPercap"].median() if not d.empty else 0
    def fmt_pop(v):
        if v >= 1e9:
            return f"{v/1e9:.2f} B"
        if v >= 1e6:
            return f"{v/1e6:.1f} M"
        return f"{v:,.0f}"
    kpi_pop_main = fmt_pop(total_pop) if not d.empty else "—"
    kpi_pop_sub = f"{total_pop:,.0f}" if not d.empty else ""
    kpi_life_txt = f"{avg_life:.1f}" if not d.empty and pd.notna(avg_life) else "—"
    kpi_gdp_txt = f"${med_gdp:,.0f}" if not d.empty and pd.notna(med_gdp) else "—"
    tbl = dash_table.DataTable(
        data=d.sort_values(["year", "country"]).to_dict("records"),
        columns=[{"name": i, "id": i} for i in ["country", "continent", "year", "lifeExp", "pop", "gdpPercap"]],
        page_size=12,
        sort_action="native",
        filter_action="native",
        style_table={"overflowX": "auto"},
        style_cell={"fontFamily": "Inter, system-ui, sans-serif", "fontSize": "13px", "padding": "6px"},
        style_header={"backgroundColor": "#f1f3f5", "fontWeight": "600"},
        style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}],
    )
    table_count_txt = f"{len(d)} filas · {year_rng[0]}–{year_rng[1]}"
    if d.empty:
        fig_bubble = go.Figure()
        fig_bubble.update_layout(title="Sin datos para el filtro", template="plotly_white")
    else:
        color_arg = bubble_color if bubble_color in ["continent", "country"] else "continent"
        if color_arg == "country" and d["country"].nunique() > 20:
            top = d.groupby("country")["pop"].max().sort_values(ascending=False).head(20).index
            d_bub = d[d["country"].isin(top)]
        else:
            d_bub = d
        fig_bubble = px.scatter(d_bub, x="gdpPercap", y="lifeExp", size="pop", color=color_arg, hover_name="country", hover_data={"year": True, "pop": ":,", "gdpPercap": ":.1f", "lifeExp": ":.1f"}, log_x=True, size_max=48, color_discrete_map=CONTINENT_COLORS if color_arg == "continent" else None, template="plotly_white", render_mode="svg")
        fig_bubble.update_layout(margin=dict(l=20, r=20, t=20, b=40), legend=dict(orientation="h", y=-0.18), xaxis_title="PIB per cápita (log)", yaxis_title="Esperanza de vida")
        fig_bubble.update_traces(marker=dict(line=dict(width=0.5, color="white"), opacity=0.78))
    if d.empty:
        fig_bar = go.Figure()
        fig_bar.update_layout(template="plotly_white", title="Sin datos")
    else:
        bar_df = d.groupby("continent", as_index=False).agg({"lifeExp": "mean", "gdpPercap": "mean", "pop": "sum"})
        fig_bar = px.bar(bar_df, x="continent", y="gdpPercap", color="continent", color_discrete_map=CONTINENT_COLORS, template="plotly_white", text_auto=".2s")
        fig_bar.update_layout(margin=dict(l=20, r=20, t=20, b=20), showlegend=False, xaxis_title="", yaxis_title="PIB pc promedio")
        fig_bar.update_traces(marker_line_width=0)
    if d.empty:
        fig_line = go.Figure()
        fig_line.update_layout(template="plotly_white", title="Sin datos")
    else:
        line_df = d.groupby(["year", "continent"], as_index=False).agg({line_metric: "mean"})
        fig_line = px.line(line_df, x="year", y=line_metric, color="continent", color_discrete_map=CONTINENT_COLORS, markers=True, template="plotly_white")
        fig_line.update_layout(margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", y=-0.18), xaxis_title="Año", yaxis_title=line_metric)
    if d.empty:
        fig_map = go.Figure()
        fig_map.update_layout(template="plotly_white", title="Sin datos")
    else:
        map_df = d.groupby(["country", "country_display"], as_index=False).agg({map_metric: "mean"})
        fig_map = px.choropleth(map_df, locations="country_display", locationmode="country names", color=map_metric, hover_name="country", color_continuous_scale="Blues", template="plotly_white")
        fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0), coloraxis_colorbar=dict(title=map_metric), geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth"))
    return str(n_countries), kpi_pop_main, kpi_pop_sub, kpi_life_txt, kpi_gdp_txt, table_count_txt, tbl, fig_bubble, fig_bar, fig_line, fig_map

@callback(Output("play_interval", "disabled"), Output("is_playing", "data"), Output("play_btn", "disabled"), Output("pause_btn", "disabled"), Input("play_btn", "n_clicks"), Input("pause_btn", "n_clicks"), State("is_playing", "data"), prevent_initial_call=True)
def toggle_play(play, pause, is_playing):
    from dash import ctx
    trig = ctx.triggered_id
    if trig == "play_btn":
        return False, True, True, False
    if trig == "pause_btn":
        return True, False, False, True
    return not is_playing, is_playing, is_playing, not is_playing

@callback(Output("year_range", "value"), Output("anim_year", "data"), Input("play_interval", "n_intervals"), State("anim_year", "data"), State("year_range", "value"), State("is_playing", "data"))
def animate(n, anim_year, year_rng, is_playing):
    if not is_playing:
        return year_rng, anim_year
    nxt = anim_year + 1 if anim_year < year_max else year_min
    return [nxt, nxt], nxt

@callback(Output("year_range", "value", allow_duplicate=True), Output("continent_filter", "value", allow_duplicate=True), Output("country_filter", "value", allow_duplicate=True), Output("anim_year", "data", allow_duplicate=True), Input("reset_btn", "n_clicks"), prevent_initial_call=True)
def reset_all(n):
    return [year_min, year_max], continents, [], year_min

if __name__ == "__main__":
    app.run(debug=True)
