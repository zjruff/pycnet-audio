"""Defines functions for visualizing apparent detections.

    Functions:

        expandDates
            Create a list encompassing all dates that fall between the
            first and last dates in a DataFrame's Date field to fill 
            in missing values.
            
        expandDetSummaryDF
            Create an 'expanded' version of the detection summary 
            DataFrame that includes all possible combinations of site,
            station, and date for all thresholds.

        formatDateTickLabels
            Format a list of dates to be displayed on the x-axis of a
            plot of apparent detections.

        formatPlotData
            Reshape and format a table of apparent detections for 
            easier plotting.

        parseDetPlotArgs
            Define command-line options for the 'plot_dets' console 
            script.

        plotDetections
            Create a plot of apparent detections of one or more classes
            by station and date.

        plotFromFile
            Plot apparent detections from a file. Target for the 
            `plot_dets` console script.

"""

import argparse
import os
import pandas as pd
import seaborn as sns
from datetime import datetime, timedelta
from matplotlib import pyplot

from pycnet.review import parseStrReviewCriteria


def expandDates(df, date_format="%Y-%m-%d"):
    """Get a list of dates that should appear in a DataFrame.

    Args:

        df (Pandas.DataFrame): A DataFrame containing a Date column.

        date_format (str): Format used by Datetime.Datetime.strptime() 
            to parse values in the Date column.

    Returns:

        list: List of all dates between the earliest and latest dates
        appearing in the Date field.
    """

    unique_dates = [datetime.strptime(x, date_format) for x in df["Date"]]

    day_1, day_n = min(unique_dates), max(unique_dates)

    dates_expanded = [day_1 + timedelta(days=i) for i in range((day_n - day_1).days + 1)]

    return dates_expanded


def expandDetSummaryDF(df):
    """Expand DataFrame to include all combinations of site, stn, date.

    Args:

        df (Pandas.DataFrame): A DataFrame containing fields called 
            Area, Site, Stn, and Date.

    Returns:

        Pandas.DataFrame: DataFrame that includes all possible 
        combinations of Area, Site, Stn, and Date for all thresholds,
        with missing values filled in with 0s.
    """
    df.fillna("", inplace=True)

    real_dates = expandDates(df)
    str_dates = [x.strftime("%Y-%m-%d") for x in real_dates]
    n_dates = len(real_dates)

    rec_days = [i + 1 for i in range(n_dates)]
    rec_weeks = [int(j / 7) + 1 for j in range(n_dates)]

    unique_areas = sorted(list(set(df["Area"])))
    unique_sites = sorted(list(set(df["Site"])))
    unique_stns = sorted(list(set(df["Stn"])))
    thresholds = sorted(list(set(df["Threshold"])))

    fill_cols = ["Area", "Site", "Stn", "Date", "Rec_Day", "Rec_Week", "Threshold"]

    fill_df = pd.DataFrame(columns = fill_cols)

    first_round = True

    for i in unique_areas:
        for j in unique_sites:
            for k in unique_stns:
                for t in thresholds:
                    new_rows = pd.DataFrame(
                        data={"Area":i, 
                            "Site":j, 
                            "Stn":k, 
                            "Date":str_dates,
                            "Rec_Day":rec_days,
                            "Rec_Week":rec_weeks, 
                            "Threshold":t}
                    )

                    if first_round:
                        fill_df = new_rows
                        first_round = False
                    else:
                        fill_df = pd.concat([fill_df, new_rows], axis=0)

    expanded_df = pd.merge(left=fill_df, right=df, how="left", on=fill_cols).fillna(value=0)

    return expanded_df


def formatDateTickLabels(df, interval=7, fill_gaps=True):
    """Format the date (x-axis) tick labels for a plot of detections.

    Args:

        df (Pandas.DataFrame): Dataframe listing apparent detections
            for each combination of station, date, detection threshold, 
            and target class, as created by 
            pycnet.review.summarizeDetections.

        interval (int): Factor by which to thin date labels for display
            on the x-axis (i.e., only label every nth date).

        fill_gaps (bool): Include blank placeholder strings as labels 
            for dates that are not displayed.  

    Returns:

        list: A list of strings representing dates in MM/DD format, 
        with empty placeholder strings if timescale=="daily".
    """

    unique_dates = sorted(list(set(df["Date"])))
    dates_formatted = [datetime.strptime(x, "%Y-%m-%d").strftime("%m/%d") for x in unique_dates]

    date_labels = [dates_formatted[i] if i % interval == 0 else '' for i in range(len(dates_formatted))]

    if not fill_gaps:
        date_labels = list(filter(lambda x: x != '', date_labels))

    return date_labels


def formatPlotData(df, criteria):
    """Filter and reshape a table of apparent detections for plotting.

    Meant to produce a dataframe in "long" format listing apparent 
    detections for a set of target classes at a corresponding set of 
    detection thresholds, which can then be plotted using seaborn.

    Args:

        df (Pandas.DataFrame): A wide-format DataFrame listing apparent
            detections for all PNW-Cnet target classes by station and
            date across a range of detection thresholds.

        criteria (dict): A dictionary mapping detection thresholds to
            target classes.

    Returns:

        Pandas.DataFrame: A long-format DataFrame listing apparent 
        detections for just the desired target classes at the detection
        threshold specified for each class.
    """

    id_cols = ["Area", "Site", "Stn", "Date", "Rec_Day", "Rec_Week", 
               "Clips", "Effort", "Threshold"]

    class_codes = criteria.keys()

    df_mod = expandDetSummaryDF(df)

    df_long = pd.melt(df_mod, 
                      id_vars=id_cols, 
                      value_vars=class_codes,
                      var_name="Class",
                      value_name="Detections"
                      )

    plot_data = pd.DataFrame(columns=df_long.keys())

    first_round = True

    for c in class_codes:
        new_rows = df_long[(df_long["Class"] == c) & (df_long["Threshold"] == criteria[c])]
        if first_round:
            plot_data = new_rows
            first_round = False
        else:
            plot_data = pd.concat([plot_data, new_rows], axis=0)

    return plot_data


def plotDetections(df, criteria, timescale="weekly", show_plot=True, dest_file=None):
    """Plot apparent detections by station for one or more classes.

    Args:

        df (Pandas.DataFrame): Dataframe listing apparent detections
            for each combination of station, date, detection threshold, 
            and target class, as created by 
            pycnet.review.summarizeDetections.

        criteria (dict): A dictionary of detection thresholds indexed
            by class codes.

        timescale (str): Either "daily" or "weekly". Temporal scale at
            which to summarize detections for the chosen class.

        show_plot (bool): Open a plot window showing the resulting 
            plot.

        dest_file (str): Path where the plot will be saved as an image 
            file, or None.

    Returns:

        Nothing.
    """
    
    time_var = "Rec_Week" if timescale == "weekly" else "Rec_Day"
    plot_data = formatPlotData(df, criteria)
    
    n_stns = len(list(set(plot_data["Stn"])))
    if n_stns == 1:
        wrap_val = 1
    elif n_stns > 8:
        wrap_val = 4
    else:
        wrap_val = 2
    
    n_classes = len(criteria)
    pal = sns.color_palette("Dark2", n_classes)
    
    plot_data["Target Class"] = plot_data["Class"]+" \u2265 "+plot_data["Threshold"].astype(str)
    
    p = sns.catplot(data=plot_data,
        x=time_var,
        y="Detections",
        hue="Target Class",
        kind="bar",
        estimator=sum,
        errorbar=None,
        col="Stn",
        col_wrap=wrap_val,
        palette=pal)

    fill_tick_gaps = timescale=="daily"

    date_labels = formatDateTickLabels(plot_data, 7, fill_tick_gaps)

    p.set_xticklabels(date_labels)
    p.set_titles(template="Station {col_name}")
    p.set(xlabel="Date", 
          ylabel="Detections")

    if show_plot:
        pyplot.show()
        
    if dest_file:
        p.savefig(dest_file, dpi=300)

    return


def plotFromFile():
    """Plot detections from a detection summary file.
    
    Arguments are read from the command line via the parseDetPlotArgs
    function defined below.
        
    Returns:
    
        Nothing.
    """
    args = parseDetPlotArgs()

    det_df = pd.read_csv(args.summary_file)
    plot_crit = parseStrReviewCriteria(args.plot_settings)

    show_plot = not args.no_show
    dest_file = args.dest_file
    
    if dest_file:
        if os.path.split(dest_file)[0] == '':
            dest_path = os.path.join(os.path.dirname(args.summary_file), dest_file)
        else:
            dest_path = dest_file
    else:
        dest_path = None

    timescale = "daily" if args.plot_daily else "weekly"

    plotDetections(det_df, plot_crit, timescale, show_plot, dest_path)
    
    return


def parseDetPlotArgs():
    """Define command-line options for the 'plot_dets' console script.

    Args:

        Nothing (reads arguments from stdin).

    Returns:

        argparse.Namespace: An argparse.Namespace object containing 
        command-line arguments in an accessible form.
    """

    parser = argparse.ArgumentParser(description="Plot apparent detections by station over time.")

    parser.add_argument("summary_file", metavar="SUMMARY_FILE", type=str, help="Path to a detection summary file.")

    parser.add_argument("plot_settings", metavar="PLOT_SETTINGS", type=str,
        help="A string specifying classes to be plotted and the detection threshold to use for each.")

    parser.add_argument("-d", dest="plot_daily", action="store_true",
        help="Plot detections by date rather than by week.")
        
    parser.add_argument("-f", dest="dest_file", type=str,
        help="Path where the plot will be saved as an image file. If only a filename is provided rather than a full path, plot will be saved in the same directory as the detection_summary file.")

    parser.add_argument("-n", dest="no_show", action="store_true",
        help="Do not open a plot display window.")

    args = parser.parse_args()

    return args
