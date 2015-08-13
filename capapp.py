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

# @app.before_request
# def before_request():
#     pass
#     #g.climbs = [1, 2, 'frog']

@app.route('/', methods = ['GET'])
def show_entries():
    #g.test = ['test','test','test']
    climb_recs = ['Nothing to recommend yet']
    print climb_recs
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
        print type(user_lfs)

        return render_template('recs.html', entries=entries,
                           user_lfs=user_lfs)
    return render_template('index.html', scroll='about', 
                           user_error = 'User not found. :[')


@app.route('/climb_search', methods=['POST'])
def climb_search():
    print request.form['climb']
    try:
        climb_id = int(request.form['climb'].split('/')[-1])
        if climb_id not in df_data.Climbs.values:
            climb_id = None
    except:
        climb_id = None
    print '--------------------------------------------------------'
    print climb_id
    





if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9999, debug=True)