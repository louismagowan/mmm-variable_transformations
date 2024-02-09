import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from scipy.stats import weibull_min
from sklearn.preprocessing import MinMaxScaler
# ------------------- VARIABLE TRANSFORMATION FUNCTIONS ------------------------

def geometric_adstock_decay(impact, decay_factor, periods):
    """
    Calculate the geometric adstock effect.

    Parameters:
        impact (float): Initial advertising impact.
        decay_factor (float): Decay factor between 0 and 1.
        periods (int): Number of periods.

    Returns:
        list: List of adstock values for each period.
    """
    adstock_values = [impact]
    
    for _ in range(1, periods):
        impact *= decay_factor
        adstock_values.append(impact)
    
    return adstock_values

def delayed_geometric_decay(impact, decay_factor, theta, L):
    """
    Calculate the geometric adstock effect with a delayed peak and a specified maximum lag length.
    
    Parameters:
        impact (float): Peak advertising impact.
        decay_factor (float): Decay factor between 0 and 1, applied throughout.
        theta (int): Period at which peak impact occurs.
        L (int): Maximum lag length for adstock effect.
        
    Returns:
        np.array: Array of adstock values for each lag up to L.
    """
    adstock_values = np.zeros(L)
    
    # Calculate adstock values
    for lag in range(L):
        if lag < theta:
            # Before peak, apply decay to grow towards peak
            adstock_values[lag] = impact * (decay_factor ** abs(lag - theta))
        else:
            # After peak, apply decay normally
            adstock_values[lag] = impact * (decay_factor ** abs(lag - theta))
    
    return adstock_values

def weibull_adstock_decay(impact, shape, scale, periods, adstock_type='cdf', normalised=True):
    """
    Calculate the Weibull PDF or CDF adstock decay for media mix modeling.

    Parameters:
        impact (float): Initial advertising impact.
        shape (float): Shape parameter of the Weibull distribution.
        scale (float): Scale parameter of the Weibull distribution.
        periods (int): Number of periods.
        adstock_type (str): Type of adstock ('cdf' or 'pdf').
        normalise (bool): If True, normalises decay values between 0 and 1,
                        otherwise leaves unnormalised.

    Returns:
        list: List of adstock-decayed values for each period.
    """
    # Create an array of time periods
    x_bin = np.arange(1, periods + 1)

    # Transform the scale parameter according to percentile of time period
    transformed_scale = round(np.quantile(x_bin, scale))

    # Handle the case when shape or scale is 0
    if shape == 0 or scale == 0:
        theta_vec_cum = np.zeros(periods)
    else:
        if adstock_type.lower() == 'cdf':
            # Calculate the Weibull adstock decay using CDF
            theta_vec = np.concatenate(([1], 1 - weibull_min.cdf(x_bin[:-1], shape, scale=transformed_scale)))
            theta_vec_cum = np.cumprod(theta_vec)
        elif adstock_type.lower() == 'pdf':
            # Calculate the Weibull adstock decay using PDF
            theta_vec_cum = weibull_min.pdf(x_bin, shape, scale=transformed_scale)
            theta_vec_cum /= np.sum(theta_vec_cum)
    
    # Return adstock decay values, normalized or not
    if normalised:
        # Normalize the values between 0 and 1 using Min-Max scaling
        norm_theta_vec_cum = MinMaxScaler().fit_transform(theta_vec_cum.reshape(-1, 1)).flatten()
        # Scale by initial impact variable
        return norm_theta_vec_cum * impact
    else:
        # Scale by initial impact variable
        return theta_vec_cum * impact


# -------------------------- TOP OF PAGE INFORMATION -------------------------

# Set browser / tab config
st.set_page_config(
    page_title="MMM App - Adstock Transformations",
    page_icon="🧊",
)

# Give some context for what the page displays
st.title('Adstock Transformations')
st.markdown("This page demonstrates the effect of various adstock \
            transformations on a variable.  \nFor these examples, let's imagine \
            that we have _some variable that represents a quantity of a particlar_ \
            _advertising channel_.  \n\nFor example, this could be the number of impressions\
            we get from Facebook.  For an online channel such as this, we might expect the impact of these ads to be immediate: \
            \n   ___We see an ad on Facebook - we either click on it, or we don't.___  \n\
            \n :blue[So, at the start of our example (_Week 1_), \
            we could have the impact of **100 impressions from Facebook**.] \
            \n\n Alternatively, for a channel like TV, we may not expect the impact of those ads  \n \
            to come through immediately - there may be some delay. \
            \n\n :green[So, at the start of our example (_Week 1_), we may have the impact of **0 Gross Rating Points (TV viewership metric)**, \
            but 7 weeks later those TV ads might reach their full impact of **100 Gross Rating Points**.]\
            \n\n**_:violet[We will use this starting value of 100 for all of our adstock examples]_**. \
            ")

st.markdown("**Reminder:** \n \
- Geometric adstock transformations have **_:red[fixed decay]_**  \n\
- Weibull adstock transformations have **_:red[flexible decay]_**")

# Starting value for adstock
initial_impact = 100

# Separate the adstock transformations into 3 tabs
tab1, tab2, tab3, tab4 = st.tabs(["Geometric", "Delayed Geometric", "Weibull CDF", "Weibull PDF"])

# -------------------------- GEOMETRIC ADSTOCK DISPLAY -------------------------
with tab1:
    st.header('Geometric Adstock Transformation')

    st.markdown("Typical values for geometric adstock: \n \
- TV: **:blue[0.3 - 0.8]** - decays slowly \n \
- OOH/Print/Radio:  **:blue[0.1 - 0.4]** - decays moderately \n \
- Digital:  **:blue[0.0 - 0.3]** - decays quickly \n")

    # User inputs
    st.subheader('User Inputs')
    num_periods = st.slider('Number of weeks after impressions first received :alarm_clock:', 1, 100, 20, key = "Geometric")
    # Let user choose decay rates to plot with
    decay_rate_1 = st.slider(':blue[Beta 1] :large_blue_square:', 0.0, 1.0, 0.3)
    # Add up to 2 more lines if the user wants it
    st.markdown('**Would you like to show multiple (3) decay lines on the plot**')
    multi_plot = st.checkbox('Okay! :grin:')
    # Create a list of decay rates
    if multi_plot:
        # Let user choose additional decay rates to plot with
        decay_rate_2 = st.slider(':red[Beta 2] :large_red_square:', 0.0, 1.0, 0.6)
        decay_rate_3 = st.slider(':green[Beta 3] :large_green_square:', 0.0, 1.0, 0.9)
        decay_rates = [decay_rate_1, decay_rate_2, decay_rate_3]
    else:
        decay_rates = [decay_rate_1]

    # Create df to store each adstock in
    all_adstocks = pd.DataFrame()
    # Iterate through decay rates and generate df of values to plot
    for i, beta in enumerate(decay_rates):
        # Get geometric adstock values, decayed over time
        adstock_df = pd.DataFrame({"Week": range(1, (num_periods + 1)),
                                ## Calculate adstock values
                                    "Adstock": geometric_adstock_decay(initial_impact, beta, num_periods),
                                    ## Format adstock labels for neater plotting
                                "Adstock Labels": [f'{x:,.0f}' for x in geometric_adstock_decay(initial_impact, beta, num_periods)], 
                                    ## Create column to label each adstock
                                    "Beta": f"Beta {i + 1}"})

        all_adstocks = pd.concat([all_adstocks, adstock_df])

    # Plot adstock values
    # Annotate the plot if user wants it
    st.markdown('**Would you like to show the adstock values directly on the plot?**')
    annotate = st.checkbox('Yes please! :pray:', key = "Geometric Annotate")
    if annotate:
        fig = px.line(all_adstocks, x = 'Week',
                y = 'Adstock', text = 'Adstock Labels',
                markers=True, color = "Beta",
                # Replaces default color mapping by value
                color_discrete_map={"Beta 1": "#636EFA",
                                        "Beta 2": "#EF553B",
                                        "Beta 3": "#00CC96"})
        fig.update_traces(textposition="bottom left")
    else:
        fig = px.line(all_adstocks, x = 'Week',
                y = 'Adstock',
                markers=True, color = "Beta",
                # Replaces default color mapping by value
                color_discrete_map={"Beta 1": "#636EFA",
                                        "Beta 2": "#EF553B",
                                        "Beta 3": "#00CC96"})
    # Format plot
    fig.layout.height = 600
    fig.layout.width = 1000
    fig.update_layout(title_text="Geometric Adstock Decayed Over Weeks", 
                    title_font = dict(size = 30))
    st.plotly_chart(fig, theme="streamlit", use_container_width=False)

# -------------------------- DELAYED GEOMETRIC ADSTOCK DISPLAY -------------------------
with tab2:
    st.header('Delayed Geometric Adstock Transformation')

    st.markdown("Typical values for geometric adstock: \n \
- TV: **:blue[0.3 - 0.8]** - decays slowly \n \
- OOH/Print/Radio:  **:blue[0.1 - 0.4]** - decays moderately \n \
- Digital:  **:blue[0.0 - 0.3]** - decays quickly \n")

    # User inputs
    st.subheader('User Inputs')
    max_lag = st.slider(':blue[Number of weeks after impressions first received :alarm_clock:]', 1, 100, 30, key = "Delayed Geometric")
    max_peak = st.slider(':blue[Number of weeks after impressions first received that max impact occurs :thermometer:]', 1, 100, 10, key = "delayed_geom_L")
    # Let user choose decay rates to plot with
    decay_rate_1 = st.slider(':blue[Beta 1] :large_blue_square:', 0.0, 1.0, 0.5, key="delay_decay")

    # Add up to 2 more lines if the user wants it
    st.markdown('**Would you like to show multiple (3) decay lines on the plot**')
    multi_plot = st.checkbox('Okay! :grin:', key = "Delay Geom Multi")
    # Create a list of decay rates
    if multi_plot:
        # Let user choose additional decay rates, lags and peaks to plot with
        decay_rate_2 = st.slider(':red[Beta 2] :large_red_square:', 0.0, 1.0, 0.6, key="delay_decay2")
        max_peak_2 = st.slider(':red[Number of weeks after impressions first received that max impact occurs :thermometer:]', 1, 100, 5, key = "delayed_geom_L 2")
        max_lag_2 = st.slider(':red[Number of weeks after impressions first received :alarm_clock:]', 1, 100, 20, key = "Delayed Geometric 2 ")
        decay_rate_3 = st.slider(':green[Beta 3] :large_green_square:', 0.0, 1.0, 0.9, key="delay_decay3")
        max_lag_3 = st.slider(':green[Number of weeks after impressions first received :alarm_clock:]', 1, 100, 20, key = "Delayed Geometric 3 ")
        max_peak_3 = st.slider(':green[Number of weeks after impressions first received that max impact occurs :thermometer:]', 1, 100, 5, key = "delayed_geom_L 3")

        # Put in lists to iterate through later
        decay_rates = [decay_rate_1, decay_rate_2, decay_rate_3]
        lags = [max_lag, max_lag_2, max_lag_3]        
        peaks = [max_peak, max_peak_2, max_peak_3]

    else:
        decay_rates = [decay_rate_1]
        lags = [max_lag]
        peaks = [max_peak]

    # Create df to store each adstock in
    all_adstocks = pd.DataFrame()
    # Iterate through decay rates and generate df of values to plot
    for i, beta in enumerate(decay_rates):
        # Get geometric adstock values, decayed over time
        adstock_df = pd.DataFrame({"Week": range(1, (lags[i] + 1)),
                                ## Calculate adstock values
                                    "Adstock": delayed_geometric_decay(impact = initial_impact,
                                                                       decay_factor = beta,
                                                                        theta = peaks[i],
                                                                        L = lags[i]),
                                    ## Format adstock labels for neater plotting
                                "Adstock Labels": [f'{x:,.0f}' for x in delayed_geometric_decay(initial_impact, beta, peaks[i], lags[i])], 
                                    ## Create column to label each adstock
                                    "Beta": f"Beta {i + 1}"})

        all_adstocks = pd.concat([all_adstocks, adstock_df])

    # Plot adstock values
    # Annotate the plot if user wants it
    st.markdown('**Would you like to show the adstock values directly on the plot?**')
    annotate = st.checkbox('Yes please! :pray:', key = "Delayed Geometric Annotate")
    if annotate:
        fig = px.line(all_adstocks, x = 'Week',
                y = 'Adstock', text = 'Adstock Labels',
                markers=True, color = "Beta",
                # Replaces default color mapping by value
                color_discrete_map={"Beta 1": "#636EFA",
                                        "Beta 2": "#EF553B",
                                        "Beta 3": "#00CC96"})
        fig.update_traces(textposition="bottom left")
    else:
        fig = px.line(all_adstocks, x = 'Week',
                y = 'Adstock',
                markers=True, color = "Beta",
                # Replaces default color mapping by value
                color_discrete_map={"Beta 1": "#636EFA",
                                        "Beta 2": "#EF553B",
                                        "Beta 3": "#00CC96"})
    # Format plot
    fig.layout.height = 600
    fig.layout.width = 1000
    fig.update_layout(title_text="Geometric Adstock Decayed Over Weeks", 
                    title_font = dict(size = 30))
    st.plotly_chart(fig, theme="streamlit", use_container_width=False)

# -------------------------- WEIBULL CDF ADSTOCK DISPLAY -------------------------
with tab3:
    st.header('Weibull CDF Adstock Transformation')
    # User inputs
    st.subheader('User Inputs')
    num_periods_2 = st.slider('Number of weeks after impressions first received :alarm_clock:',
                               1, 100, 20, key = "Weibull CDF Periods")
    # Let user choose shape and scale parameters to compare two Weibull PDF decay curves simultaneously
    # Params for Line A
    shape_parameter_A = st.slider(':triangular_ruler: :blue[Shape of Line A] :large_blue_square:', 
                                  0.0, 10.0, 0.1, key = "Weibull CDF Shape A")
    scale_parameter_A = st.slider(':blue[Scale of Line A] :large_blue_square:',
                                   0.0, 1.0, 0.1, key = "Weibull CDF Scale A")
    
    # Calculate weibull pdf adstock values, decayed over time for both sets of params
    adstock_series_A = weibull_adstock_decay(initial_impact, shape_parameter_A,
                                                  scale_parameter_A, num_periods_2,
                                                  adstock_type='cdf', normalised=True)
    
    # Create df of adstock values, to plot with
    adstock_df_A = pd.DataFrame({"Week": range(1, (num_periods_2 + 1)),
                                "Adstock": adstock_series_A,
                                "Line": "Line A"})
    
    # Create plotting df
    weibull_pdf_df = adstock_df_A.copy()
    
    # Plot 2nd line if user desires values
    st.markdown('**Would you like to add a second line to the plot?**')
    second_cdf = st.checkbox('Okay! :grin:', key = "Add 2nd Weibull CDF")

    if second_cdf:
        # Params for Line B
        shape_parameter_B = st.slider(':triangular_ruler: :red[Shape of Line B] :large_red_square:', 
                                    0.0, 10.0, 9.0, key = "Weibull CDF Shape B")
        scale_parameter_B = st.slider(':red[Scale of Line B] :large_red_square:', 
                                    0.0, 1.0, 0.5, key = "Weibull CDF Scale B")
        # Calculate weibull pdf adstock values, decayed over time for both sets of params
        adstock_series_B = weibull_adstock_decay(initial_impact, shape_parameter_B,
                                                    scale_parameter_B, num_periods_2,
                                                    adstock_type='cdf', normalised=True)

        # Create df of adstock values, to plot with
        adstock_df_B = pd.DataFrame({"Week": range(1, (num_periods_2 + 1)),
                                    "Adstock": adstock_series_B,
                                    "Line": "Line B"})
        # Create plotting df
        weibull_pdf_df = pd.concat([adstock_df_A, adstock_df_B])

    # Multiply by 100 to get back to scale of initial impact (100 FB impressions)
    weibull_pdf_df.Adstock = weibull_pdf_df.Adstock
    # Format adstock labels for neater plotting
    weibull_pdf_df["Adstock Labels"] = weibull_pdf_df.Adstock.map('{:,.0f}'.format)

    # Plot adstock values
    # Annotate the plot if user wants it
    st.markdown('**Would you like to show the adstock values directly on the plot?**')
    annotate = st.checkbox('Yes please! :pray:', key = "Weibull CDF Annotate")
    if annotate:
        fig = px.line(weibull_pdf_df, x = 'Week',
                y = 'Adstock', text = 'Adstock Labels',
                markers=True, color = "Line",
                # Replaces default color mapping by value
                color_discrete_map={"Line A": "#636EFA",
                                        "Line B": "#EF553B"})
        fig.update_traces(textposition="bottom left")
    else:
        fig = px.line(weibull_pdf_df, x = 'Week',
                y = 'Adstock',
                markers=True, color = "Line",
                # Replaces default color mapping by value
                color_discrete_map={"Line A": "#636EFA",
                                        "Line B": "#EF553B"})
    # Format plot
    fig.layout.height = 600
    fig.layout.width = 1000
    fig.update_layout(title_text="Weibull CDF Adstock Decayed Over Weeks", 
                    title_font = dict(size = 30))
    st.plotly_chart(fig, theme="streamlit", use_container_width=False)

# -------------------------- WEIBULL PDF ADSTOCK DISPLAY -------------------------
with tab4:
    st.header('Weibull PDF Adstock Transformation')

    # User inputs
    st.subheader('User Inputs')
    num_periods_3 = st.slider('Number of weeks after impressions first received :alarm_clock:',
                               1, 100, 20, key = "Weibull PDF Periods")
    # Let user choose shape and scale parameters to compare two Weibull PDF decay curves simultaneously
    # Params for Line A
    shape_parameter_A = st.slider(':triangular_ruler: :blue[Shape of Line A] :large_blue_square:',
                                   0.0, 10.0, 2.0, key = "Weibull PDF Shape A")
    scale_parameter_A = st.slider(':blue[Scale of Line A] :large_blue_square:', 
                                  0.0, 1.0, 0.5, key = "Weibull PDF Scale A")
    
    # Calculate weibull pdf adstock values, decayed over time for both sets of params
    adstock_series_A = weibull_adstock_decay(initial_impact, shape_parameter_A,
                                                  scale_parameter_A, num_periods_3,
                                                  adstock_type='pdf', normalised=True)  

    # Create df of adstock values, to plot with
    adstock_df_A = pd.DataFrame({"Week": range(1, (num_periods_3 + 1)),
                                "Adstock": adstock_series_A,
                                "Line": "Line A"})  
    
    # Create plotting df
    weibull_pdf_df = adstock_df_A.copy()

    # Plot 2nd line if user desires values
    st.markdown('**Would you like to add a second line to the plot?**')
    second_pdf = st.checkbox('Okay! :grin:', key = "Add 2nd Weibull PDF")

    if second_pdf:
        # Params for Line B
        shape_parameter_B = st.slider(':triangular_ruler: :red[Shape of Line B] :large_red_square:',
                                    0.0, 10.0, 0.5, key = "Weibull PDF Shape B")
        scale_parameter_B = st.slider(':red[Scale of Line B] :large_red_square:', 
                                    0.0, 1.0, 0.01, key = "Weibull PDF Scale B")

        # Calculate weibull pdf adstock values, decayed over time for both sets of params
        adstock_series_B = weibull_adstock_decay(initial_impact, shape_parameter_B,
                                                    scale_parameter_B, num_periods_3,
                                                    adstock_type='pdf', normalised=True)
    
        # Create df of adstock values, to plot with
        adstock_df_B = pd.DataFrame({"Week": range(1, (num_periods_3 + 1)),
                                    "Adstock": adstock_series_B,
                                    "Line": "Line B"})
        # Create plotting df
        weibull_pdf_df = pd.concat([adstock_df_A, adstock_df_B])

    # Multiply by 100 to get back to scale of initial impact (100 FB impressions)
    weibull_pdf_df.Adstock = weibull_pdf_df.Adstock
    # Format adstock labels for neater plotting
    weibull_pdf_df["Adstock Labels"] = weibull_pdf_df.Adstock.map('{:,.0f}'.format)

    # Plot adstock values
    # Annotate the plot if user wants it
    st.markdown('**Would you like to show the adstock values directly on the plot?**')
    annotate = st.checkbox('Yes please! :pray:', key = "Weibull PDF Annotate")
    if annotate:
        fig = px.line(weibull_pdf_df, x = 'Week',
                y = 'Adstock', text = 'Adstock Labels',
                markers=True, color = "Line",
                # Replaces default color mapping by value
                color_discrete_map={"Line A": "#636EFA",
                                        "Line B": "#EF553B"})
        fig.update_traces(textposition="bottom left")
    else:
        fig = px.line(weibull_pdf_df, x = 'Week',
                y = 'Adstock',
                markers=True, color = "Line",
                # Replaces default color mapping by value
                color_discrete_map={"Line A": "#636EFA",
                                        "Line B": "#EF553B"})
    # Format plot
    fig.layout.height = 600
    fig.layout.width = 1000
    fig.update_layout(title_text="Weibull PDF Adstock Decayed Over Weeks", 
                    title_font = dict(size = 30))
    st.plotly_chart(fig, theme="streamlit", use_container_width=False)