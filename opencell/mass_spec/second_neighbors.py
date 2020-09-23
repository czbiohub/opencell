import pandas as pd
from itertools import repeat
import validations as vali
from multiprocessing import Pool


def simple_second_neighbor(network, target_col, prey_col, threshold=3):
    """
    Find prey-prey second neighbors by a simple function of # mutual targets
    """
    network = network[[target_col, prey_col]]

    prey_uniques = set(network[prey_col].to_list())

    multi_args = zip(prey_uniques, repeat(network), repeat(target_col),
        repeat(prey_col), repeat(threshold))

    # multi processing
    p = Pool()
    sn_tables = p.starmap(aux_simple_second, multi_args)
    p.close()
    p.join()

    sn_table = pd.concat(sn_tables)
    sn_table.sort_index(axis=1, inplace=True)

    # remove duplicates
    sn_drops = vali.convert_to_unique_interactions(sn_table, 'prey', 'prey_1')

    # remove direct interactions
    network_uniques = vali.convert_to_unique_interactions(
        network, target_col, prey_col)

    sn_merge = sn_drops.merge(
        network_uniques, on=['prot_1', 'prot_2'], how='left', indicator=True)

    sn_merge = sn_merge[sn_merge['_merge'] == 'left_only'].drop(columns='_merge')

    sn_final = sn_merge.merge(
        sn_table.rename(columns={'prey': 'prot_1', 'prey_1': 'prot_2'}),
        on=['prot_1', 'prot_2'])

    # sort index, reset inplace and return table
    sn_final.sort_index(axis=1, inplace=True)
    sn_final.sort_values(by=['prot_1', 'prot_2'], inplace=True)
    sn_final.reset_index(drop=True, inplace=True)

    return sn_final


def aux_simple_second(prey, network, target_col, prey_col, threshold=3):
    """
    core function for simple_second_neighbor, separated for
    multi-processing Pool

    Finds all prey second neighbors with a given threshold of mutual targets
    """

    prey_specific = network[network[prey_col] == prey]
    specific_targets = prey_specific[target_col].to_list()
    specific_preys = network[network[target_col].isin(specific_targets)]

    # count co-occuring preys, filter to second neighbors
    neighbor_counts = specific_preys[prey_col].value_counts()
    filtered_count = neighbor_counts[neighbor_counts >= threshold]
    second_neighbors = filtered_count.index.to_list()

    # process table
    sn_table = specific_preys[specific_preys[prey_col].isin(second_neighbors)]
    sn_table = sn_table.groupby(prey_col)[target_col].apply(list)
    sn_table = pd.DataFrame(sn_table.reset_index())

    sn_table.rename(
        columns={'target': 'shared_targets', 'prey': 'prey_1'}, inplace=True)

    # include orginal prey in the database
    sn_table['prey'] = prey

    return sn_table
