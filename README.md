# From Visit to Purchase

DSML 2120 Lab 4.3 · Lifu Deng

A Streamlit dashboard for an e-commerce manager reviewing a synthetic website funnel. Filter by date, traffic source, and device to see where shoppers drop off and compare purchase conversion.

Run locally with `python -m pip install -r requirements.txt` and then `python -m streamlit run app.py`.

The course dataset is saved under `data/`. Purchase conversion divides total purchases by total sessions. Stage drop-off divides the loss from the previous stage by the previous stage's count. Rows missing a value needed by the dashboard are excluded.
