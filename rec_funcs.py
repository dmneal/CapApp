import graphlab as gl
import numpy as np
import pandas as pd
import pickle, json
from collections import defaultdict



def determine_input(input_str, df_data, user_map):
    '''Determine the user id intiger from either a user name
    or user id.
    
    Args:
        input_str (string): A string that is either the user
                            name or id in string form
        df_data (pd dataframe): df of users' star ratings
        user_map (dict): user name to id map

    Returns:
        user_id (int)
        or None if not in system
    '''


    try:
        id_val = int(input_str)
        if id_val in df_data.User.values:
            return id_val
        else: 
            return None
    except ValueError:
        if input_str in user_map:
            return user_map[input_str]
        else:
            return None

def user_rated_visited(user_id, df_data, df_raw):
    ''' Find areas user has visited and a comfortable
    max difficulty for them based on climbs they have
    rated.
    
    Args:
        user_id (int): id of user
        df_data (pd dataframe): dataframe with users' 
                                star ratings.
        df_raw (pd dataframe): dataframe with climb
                               feature data
    
    Returns:
        visited (set): areas user has visited
        rating_max (float): hardest climb that should
                            be recommended
    '''
    climbs_rated = df_data[df_data.User==user_id].Climb
    visited = set(df_raw.loc[climbs_rated].sub_location.values)
  
    #Finder user difficulty rating range from stared climbs
    user_ratings = df_raw.loc[climbs_rated].rating
    user_rating_std = user_ratings.std()
    user_rating_mean = user_ratings.mean()
    rating_max = user_rating_mean+user_rating_std
    
    return visited, rating_max
   
#Find climb locations to recommend
def rec_loc_climb(user_id, visited, rating_max, df_raw,
                  model, verbose=False, n_areas=3, n_climbs=10):
    '''Recomend new locations and climbs based on input model.

    Args:
        user_id (int): user id from mountainproject.com
        visited (iterable): areas (str) user has visited
        rating_max (float): hardes climb to recommend
        df_raw (pd dataframe): climb feature data
        model (Graphlab model): model to make recs from
        verbose (bool): for printing recommendations
        n_area (int): number of areas to recommend
        n_climbs (int): number of climbs to rec in each areas

    Returns:
        loc_recs (list of str): areas to recommend
        loc_climb_recs (dict): map of areas to list of climb_ids
    '''

    climb_recs = model.recommend(users=[user_id], k=13000)
    loc_climb_recs = defaultdict(list)
    loc_recs = []
    n_recs = 0
    for rec in climb_recs:
        climb = rec['Climb']
        if df_raw.loc[climb].rating < rating_max:
            loc = df_raw.loc[climb].sub_location
            if loc not in (list(visited) + loc_recs):
                loc_climb_recs[loc] += [climb]
                if len(loc_climb_recs[loc]) == n_climbs:
                    loc_recs += [loc]
                    n_recs += 1
                    if n_recs == n_areas:
                        break
    if verbose:
        for loc in loc_recs:
            print loc
            print loc_climb_recs[loc]
    return loc_recs, loc_climb_recs
    
def get_latent_user(user_id, model):
    '''Find user latent information from model
    Args:
        user_id (int): user id
        model (Graphlab model): model to pull latent features from

    Returns:
        df_fac_user (iterable): latent feature scores
    '''
    coefs = model.get('coefficients')
    df_fac_user = pd.DataFrame(np.array(coefs['User']['factors']))
    df_fac_user.set_index(np.array(coefs['User']['User']), inplace=True)
    return df_fac_user.loc[user_id]

def rec_loc_climb_sim(model, df_raw, climb_ids=[106129861, 106460891], 
                      rating_max = None,
                      verbose=False, 
                      n_areas=3, n_climbs=10, star_min=3.5):
    '''Recommend climbs and areas based on item similarity of input
    climbs.
    Args:
        model (Graphlab model): model to use.
        df_raw (pd dataframe): df of climb feature data
        climb_ids (iterable of ints): climb ids to find similar
        rating_max (float): highest difficulty for user, set to 
                            difficulty of climb_ids if None.
        verbose (bool): print results if True
        n_area (int): number of areas to recommend
        n_climbs (int): number of climbs to recommend for areas
        star_min (float): min star score of climb to recommend

    Returns:
        loc_recs (list of str): areas to recommend
        loc_climb_recs (dict): map of areas to list of climb_ids
    '''

    #Recommend locations and climbs based on similarities to input climbs
    rec_SF = model.get_similar_items(climb_ids, k=13000)
    top_recs = rec_SF.to_dataframe().sort(['distance'],
                                          ascending=False).similar
    visited = set(df_raw.loc[climb_ids].sub_location.values)
    
    if not rating_max:
    #Finder user difficulty rating range from climbs
        user_ratings = df_raw.loc[climb_ids].rating
        print 'user_rating', user_ratings
        if len(user_ratings)>1:
            rating_max = user_ratings.std()+user_ratings.mean()
        else:
            rating_max = user_ratings.mean()
    
    print "Rating Max:", rating_max
    
    loc_climb_recs = defaultdict(list)
    loc_recs = []
    n_recs = 0
    for climb in top_recs:
        if df_raw.loc[climb].stars > star_min:
            if df_raw.loc[climb].rating < rating_max:
                loc = df_raw.loc[climb].sub_location
                if loc not in (list(visited) + loc_recs):
                    loc_climb_recs[loc] += [climb]
                    if len(loc_climb_recs[loc]) == n_climbs:
                        loc_recs += [loc]
                        n_recs += 1
                        if n_recs == n_areas:
                            break
    
    if verbose:
        for loc in loc_recs:
            print loc
            print loc_climb_recs[loc]
    return loc_recs, loc_climb_recs


def get_latent_climbs(climb_ids, model):
    '''Get latent features of climbs

    Args:
        climb_ids (list of ints): climb ids
        model (Graphlab model): model to use

    Returns:
        climb_av (list of floats): Average latent features scores
                                   of input climbs
    '''

    coefs = model.get('coefficients')
    df_fac_climb = pd.DataFrame(np.array(coefs['Climb']['factors']))
    df_fac_climb.set_index(np.array(coefs['Climb']['Climb']), inplace=True)
    climb_av = np.zeros(4)
    for climb_id in climb_ids:
        climb_av += df_fac_climb.loc[climb_id]
    return climb_av

def rec_loc_climb_lf(input_lf, climb_type, model, df_raw, df_data,
                    rating_max=18, star_min=3.5, n_climbs=10, 
                     n_areas=3, verbose=False):
    '''Recommend climbs based on input latent features.  

    Args:
        input_lf (numpy.array): array of latent feature scores
        climb_type (str): climb type to filter by ('Sport' or 'Trad')
        model (Graphlab model): model must be a matrix factorization
        df_raw (pd dataframe): 
    '''

    scale_ls = 0.05 * input_lf
    coefs = model.get('coefficients')
    df_fac_climb = pd.DataFrame(np.array(coefs['Climb']['factors']))
    df_rec = pd.DataFrame(scale_ls.dot(df_fac_climb.values.T))
    df_rec.set_index(np.array(coefs['Climb']['Climb']), inplace=True)

    df_rec.sort(0, ascending=False, inplace=True)

    df_rec = df_rec[df_raw['stars']>star_min]
    df_rec = df_rec[df_raw['type']==climb_type]

    loc_climb_recs = defaultdict(list)
    loc_recs = []
    n_recs = 0
    for climb in df_rec.index:
        if df_raw.loc[climb].rating < rating_max:
            loc = df_raw.loc[climb].sub_location
            if loc not in (loc_recs):
                loc_climb_recs[loc] += [climb]
                if len(loc_climb_recs[loc]) == n_climbs:
                    loc_recs += [loc]
                    n_recs += 1
                    if n_recs == n_areas:
                        break
    if verbose:
        for loc in loc_recs:
            print loc
            print loc_climb_recs[loc]
    return loc_recs, loc_climb_recs

if __name__ == "__main__":
    #user name to user id dict
    with open('user_map.p','r') as f:
        user_map = pickle.load(f)

    #star rating and climb data
    df_data = pd.read_csv('star5.csv')
    with open('df_raw_star5.p','r') as f:
        df_raw = pickle.load(f)

    #load in recommendation models
    sim_mod = gl.load_model('sim_mod')
    rfr_mod = gl.load_model('rfm_mod_15')
    rfr_mod_lf = gl.load_model('rfm_mod_features_extracted')
    
    #user input
    input_str = 'LauraColyer'
    user_id = determine_input(input_str, df_data, user_map)
    
    visited, rating_max = user_rated_visited(user_id, df_data, df_raw)

    #Get climb recomendations from item similarity model
    loc_recs_sim, loc_climb_recs_sim = rec_loc_climb(user_id,
                                                  visited,
                                                  rating_max,
                                                  df_raw,
                                                  sim_mod,
                                                  verbose=True)
    
    #Get climb recomendations from item similarity model
    loc_recs_rfr, loc_climb_recs_rfr = rec_loc_climb(user_id,
                                                  visited,
                                                  rating_max,
                                                  df_raw,
                                                  rfr_mod,
                                                  verbose=True)
    print get_latent_user(user_id, rfr_mod_lf)
    
    loc_recs, loc_climb_recs = rec_loc_climb_sim(rfr_mod, 
                        df_raw, 
                        climb_ids=[106460891, 106460901, 105875465],
                        rating_max = 18,
                        verbose=True) 
    
    print get_latent_climbs([106460891, 106460901, 105875465], rfr_mod_lf)

    input_lf = np.array([-1,-1,1,-1])
    climb_type = 'Trad'
    star_min = 3
    rating_max = 20
    model = rfr_mod_lf
    df_raw
    df_data
    loc_recs, loc_climb_recs=rec_loc_climb_lf(input_lf, climb_type, model, df_raw, df_data,
                        rating_max=rating_max, star_min=star_min,
                    verbose=True)