from flask import Flask, g, render_template, redirect, url_for, \
    request, flash
import pickle
import graphlab as gl
import pandas as pd
import rec_funcs as rf


with open('climb_map.p','r') as f:
    climb_map = pickle.load(f)

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


# create our little application :)
app = Flask(__name__)
app.secret_key = 'some_secret'
app.config.from_object(__name__)


@app.route('/', methods = ['GET'])
def show_entries():
    return render_template('index.html')

@app.route('/user_search', methods=['POST'])
def user_search():
    
    user_id = rf.determine_input(request.form['user'], df_data, user_map)
    
    if user_id:
        visited, rating_max = rf.user_rated_visited(user_id, df_data, df_raw)
        loc_recs, loc_climb_recs = rf.rec_loc_climb(user_id, visited, 
                                                 rating_max, df_raw,
                                                 rfr_mod)
        entries = {'locations':loc_recs}
        for loc in loc_recs:
            entries[loc+'_id'] = loc_climb_recs[loc]
            entries[loc] = []
            for climb_id in loc_climb_recs[loc]:
                entries[loc] += [climb_map[climb_id]]

        user_lfs = rf.get_latent_user(user_id, rfr_mod_lf).tolist()

        return render_template('user_recs.html', entries=entries,
                           user_lfs=user_lfs)
    return render_template('index.html', scroll='about', 
                           user_error = 'User not found. :[')


@app.route('/climb_search', methods=['POST'])
def climb_search():
    climbs = request.form['climb'].split(',')
    climb_ids = []
    
    try:
        for climb in climbs:
            climb_id_cur = int(climb.strip().split('/')[-1])
            if climb_id_cur in df_data.Climb.values:
                climb_ids += [climb_id_cur]
    except:
        climb_ids = None
    
    
    if climb_ids:        
        loc_recs, loc_climb_recs = rf.rec_loc_climb_sim(rfr_mod, 
                                            df_raw, 
                                            climb_ids=climb_ids)
        entries = {'locations':loc_recs}
        for loc in loc_recs:
                entries[loc+'_id'] = loc_climb_recs[loc]
                entries[loc] = []
                for climb_id in loc_climb_recs[loc]:
                    entries[loc] += [climb_map[climb_id]]

        user_lfs = rf.get_latent_climbs(climb_ids, rfr_mod_lf).tolist()

        return render_template('user_recs.html', entries=entries,
                           user_lfs=user_lfs)

    return render_template('index.html', scroll='download', 
                           climb_error = 'Climb not found. :[')





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=True)