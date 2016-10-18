#!/bin/python

# This script documents converting Yu's 'final_3.tsv' to 'data.tsv' intended to be imported into
# the whatisit application as sample data

import os
import pandas


input_file = 'final_3.csv'
if os.path.exists(input_file):
    raw = pandas.read_csv(input_file)
    data = pandas.DataFrame(columns=['report_id',
                                     'report_text',
                                     'disease_state_label',
                                     'historicity_label',
                                     'uncertainty_label',
                                     'quality_label'])

    # Order id will be the identifier
    data['report_id'] = raw['order_deid']
    data['report_text'] = raw['rad_report']
    data['disease_state_label'] = raw['disease_state_label']
    data['uncertainty_label'] = raw['uncertainty_label']
    data['quality_label'] = raw['quality_label']
    data['historicity_label'] = raw['historicity_label']
    data.to_csv('data.tsv',sep='\t',index=False)

else:
    print("Please make sure %s is in the present working directory!" %(input_file))
