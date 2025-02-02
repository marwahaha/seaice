__author__ = "Marc Oggier"
__license__ = "GPL"
__version__ = "0.1"
__maintainer__ = "Marc Oggier"
__contact__ = "Marc Oggier"
__email__ = "moggier@alaska.edu"
__status__ = "development"
__date__ = "2017/09/13"
__name__ = "climatology"

import numpy as np
import pandas as pd
import seaice



def DD_fillup(ics_stack, DD, freezup_dates):
    import datetime

    for f_day in ics_stack.date.unique():
        # look for freezup_day
        if isinstance(f_day, np.datetime64):
            f_day = datetime.datetime.utcfromtimestamp(
                (f_day - np.datetime64('1970-01-01T00:00:00')) / np.timedelta64(1, 's'))
        f_day = datetime.datetime(f_day.year, f_day.month, f_day.day)
        if f_day < datetime.datetime(f_day.year, 9, 1):
            freezup_day = datetime.datetime.fromordinal(freezup_dates[f_day.year])
        else:
            freezup_day = datetime.datetime.fromordinal(freezup_dates[f_day.year + 1])

        # look for number of freezing/thawing degree day:
        if DD[f_day][1] < 0:
            ics_stack.loc[ics_stack.date == f_day, 'DD'] = DD[f_day][1]
        else:
            ics_stack.loc[ics_stack.date == f_day, 'DD'] = DD[f_day][0]

        ics_stack.loc[ics_stack.date == f_day, 'FDD'] = DD[f_day][0]
        ics_stack.loc[ics_stack.date == f_day, 'TDD'] = DD[f_day][1]
        ics_stack.loc[ics_stack.date == f_day, 'freezup_day'] = ['a']
        ics_stack.loc[ics_stack.date == f_day, 'freezup_day'] = [freezup_day]
    return CoreStack(ics_stack)


def stack_DD_fud(ics_data, DD, freezup_dates):
    ics_data_stack = CoreStack()
    for ii_core in ics_data.keys():
        core = ics_data[ii_core]
        ics_data_stack = ics_data_stack.add_profiles(core.profiles)

    for ii_day in ics_data_stack.date.unique():
        variable_dict = {'date': ii_day}
        ii_day = pd.DatetimeIndex([ii_day])[0].to_datetime()

        # freezup day:
        if ii_day < datetime.datetime(ii_day.year, 9, 1):
            freezup_day = datetime.datetime.fromordinal(freezup_dates[ii_day.year - 1])
        else:
            freezup_day = datetime.datetime.fromordinal(freezup_dates[ii_day.year])
        # DD
        if DD[ii_day][1] < 0:
            data = [[DD[ii_day][0], DD[ii_day][1], DD[ii_day][1], np.datetime64(freezup_day)]]
        else:
            data = [[DD[ii_day][0], DD[ii_day][1], DD[ii_day][0], np.datetime64(freezup_day)]]
        data_label = ['date', 'FDD', 'TDD', 'DD', 'freezup_day']
        data = pd.DataFrame(data, columns=data_label)

        ics_data_stack = ics_data_stack.add_variable(variable_dict, data)
    return ics_data_stack


def grouped_stat(ics_stack, variables, stats, bins_DD, bins_y, comment=False):
    ics_stack = ics_stack.reset_index(drop=True)
    y_cuts = pd.cut(ics_stack.y_mid, bins_y, labels=False)
    t_cuts = pd.cut(ics_stack.DD, bins_DD, labels=False)

    if not isinstance(variables, list):
        variables = [variables]
    if not isinstance(stats, list):
        stats = [stats]

    temp_all = pd.DataFrame()
    for ii_variable in variables:
        if comment:
            print('\ncomputing %s' % ii_variable)
        data = ics_stack[ics_stack.variable == ii_variable]
        data_grouped = data.groupby([t_cuts, y_cuts])

        for ii_stat in stats:
            if comment:
                print('\tcomputing %s' % ii_stat)
            func = "groups['" + ii_variable + "']." + ii_stat + "()"
            stat_var = np.nan * np.ones((bins_DD.__len__() - 1, bins_y.__len__()-1))
            core_var = [[[None] for x in range(bins_y.__len__())] for y in range(bins_DD.__len__() - 1)]
            for k1, groups in data_grouped:
                stat_var[int(k1[0]), int(k1[1])] = eval(func)
                core_var[int(k1[0])][int(k1[1])] = [list(groups.dropna(subset=[ii_variable])
                                                         ['name'].unique())]
            for ii_bin in range(stat_var.__len__()):
                temp = pd.DataFrame(stat_var[ii_bin], columns=[ii_variable])
                temp = temp.join(pd.DataFrame(core_var[ii_bin], columns=['collection']))
                DD_label = 'DD-' + str(bins_DD[ii_bin]) + '_' + str(bins_DD[ii_bin + 1])
                data = [str(bins_DD[ii_bin]), str(bins_DD[ii_bin + 1]), DD_label, int(ii_bin), ii_stat,
                        ii_variable, ics_stack.v_ref.unique()[0]]
                columns = ['DD_min', 'DD_max', 'DD_label', 'DD_index', 'stats', 'variable', 'v_ref']
                index = np.array(temp.index.tolist())  #[~np.isnan(temp[ii_variable].tolist())]
                temp = temp.join(pd.DataFrame([data], columns=columns, index=index))
                temp = temp.join(pd.DataFrame(index, columns=['y_index'], index=index))
                for row in temp.index.tolist():
                    #temp.loc[temp.index == row, 'n'] = temp.loc[temp.index == row, 'collection'].__len__()
                    if temp.loc[temp.index == row, 'collection'][row] is not None:
                        temp.loc[temp.index == row, 'n'] = temp.loc[temp.index == row, 'collection'][row].__len__()
                    else:
                        temp.loc[temp.index == row, 'n'] = 0
                columns = ['y_low', 'y_sup', 'y_mid']
                t2 = pd.DataFrame(columns=columns)
                # For step profile, like salinity
                # if ii_variable in ['salinity']:
                if not ics_stack[ics_stack.variable == ii_variable].y_low.isnull().any():
                    for ii_layer in index:
                        data = [bins_y[ii_layer], bins_y[ii_layer + 1],
                                (bins_y[ii_layer] + bins_y[ii_layer + 1]) / 2]
                        t2 = t2.append(pd.DataFrame([data], columns=columns, index=[ii_layer]))
                # For linear profile, like temperature
                # if ii_variable in ['temperature']:
                elif ics_stack[ics_stack.variable == ii_variable].y_low.isnull().all():
                    for ii_layer in index:
                        data = [np.nan, np.nan, (bins_y[ii_layer] + bins_y[ii_layer + 1]) / 2]
                        t2 = t2.append(pd.DataFrame([data], columns=columns, index=[ii_layer]))

                if temp_all.empty:
                    temp_all = temp.join(t2)
                else:
                    temp_all = temp_all.append(temp.join(t2), ignore_index=True)

    data_grouped = ics_stack.groupby([t_cuts, ics_stack['variable']])

    grouped_dict = {}
    for var in variables:
        grouped_dict[var] = [[] for ii_DD in range(bins_DD.__len__()-1)]

    for k1, groups in data_grouped:
        if k1[1] in variables:
            grouped_dict[k1[1]][int(k1[0])] = groups['name'].unique().tolist()

    return seaice.core.corestack.CoreStack(temp_all.reset_index(drop=True)), grouped_dict


def compute_climatology(ics_stack, bins_DD, bins_y, variables=None, ice_core_reference=['top']):
    """

    :param ics_stack:
    :param ice_core_reference:
        ice_core_reference is 'top' by default
    :return:
    """

    if not isinstance(ice_core_reference, list):
        ice_core_reference = [ice_core_reference]

    if variables is None:
        variables = ics_stack.variable.unique().tolist()

    for ref in ice_core_reference:
        print('\nVertical zero reference at:\t')
        # setting
        if ref == 'bottom':
            ics_stack = ics_stack.set_reference('bottom')
            print('ice/water interface (bottom)')
        else:
            ics_stack = ics_stack
            print('ice/snow interface (top)')

        # creating a 2D space depth (y) and time (TDD/FDD)
        stats = ['mean', 'std', 'min', 'max']
        for f_variable in variables:
            ics_stack[f_variable] = ics_stack[f_variable].astype(float)

        ics_climat, ics_climat_dict = grouped_stat(ics_stack, variables, stats, bins_DD, bins_y, comment=True)
        return ics_climat, ics_climat_dict
