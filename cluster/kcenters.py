# Author: Maxwell I. Zimmerman <mizimmer@wustl.edu>,
#         Gregory R. Bowman <gregoryrbowman@gmail.com>
# Contributors:
# Copyright (c) 2016, Washington University in St. Louis
# All rights reserved.
# Unauthorized copying of this file, via any medium is strictly prohibited
# Proprietary and confidential

from __future__ import print_function, division, absolute_import

import sys

from .utils import assign_to_nearest_center, requires_concatenated_trajectories

from ..exception import ImproperlyConfigured

import numpy as np


def _kcenters_helper(
        traj, distance_method, n_clusters, dist_cutoff,
        cluster_centers, random_first_center, output):

    if n_clusters is None and dist_cutoff is None:
        raise ImproperlyConfigured(
            "KCenters must specify 'n_clusters' xor 'distance_cutoff'")
    elif n_clusters is None and dist_cutoff is not None:
        n_clusters = np.inf
    elif n_clusters is not None and dist_cutoff is None:
        dist_cutoff = 0

    new_center_index = 0
    n_frames = len(traj)
    assignments = np.zeros(n_frames, dtype=int)
    distances = np.empty(n_frames, dtype=float)
    distances.fill(np.inf)
    cluster_center_inds = []
    max_distance = np.inf
    cluster_num = 0

    if cluster_centers is not None:
        if output:
            output.write("Updating assignments to previous cluster centers\n")
        cluster_center_inds, assignments, distances = assign_to_nearest_center(
            traj, cluster_centers, distance_method)
        cluster_num = len(cluster_center_inds) + 1
        new_center_index = np.argmax(distances)
        max_distance = np.max(distances)

    while (cluster_num < n_clusters) and (max_distance > dist_cutoff):
        dist = distance_method(traj, traj[new_center_index])
        inds = (dist < distances)
        distances[inds] = dist[inds]
        assignments[inds] = cluster_num
        cluster_center_inds.append(new_center_index)
        new_center_index = np.argmax(distances)
        max_distance = np.max(distances)
        if output:
            output.write(
                "kCenters cluster "+str(cluster_num) +
                " will continue until max-distance, " +
                '{0:0.6f}'.format(max_distance) + ", falls below " +
                '{0:0.6f}'.format(dist_cutoff) +
                " or num-clusters reaches "+str(n_clusters)+'\n')
        cluster_num += 1
    cluster_centers = traj[cluster_center_inds]

    return cluster_center_inds, assignments, distances


@requires_concatenated_trajectories
def kcenters(
        traj, distance_method, n_clusters=None, dist_cutoff=None,
        init_cluster_centers=None, random_first_center=False,
        output=sys.stdout):

    cluster_center_inds, assignments, distances = _kcenters_helper(
        traj, distance_method, n_clusters=n_clusters, dist_cutoff=dist_cutoff,
        cluster_centers=init_cluster_centers,
        random_first_center=random_first_center, output=output)

    return cluster_center_inds, assignments, distances