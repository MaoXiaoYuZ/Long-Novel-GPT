from promptflow.core import tool

import json

import numpy as np

@tool
def parse_response(response_msgs, plot_chunks, text_chunks):
    from prompts.prompt_utils import match_first_json_block
    content = response_msgs[-1]['content']
    content = match_first_json_block(content)
    plot2text = json.loads(content)

    plot2text = {int(k) - 1 : [e - 1 for e in v] for k, v in plot2text.items()}
    print(plot2text)
    plot_text_pair = []

    # ploti_l = np.array(list(plot2text.keys()))
    # textl_l = np.array([e[0] for e in plot2text.values()])

    # if not (np.all(ploti_l[1:] >= ploti_l[:-1]) and np.all(textl_l[1:] >= textl_l[:-1])):
    #     return []
    
    # if not (ploti_l[0] == 0 and textl_l[0] == 0):
    #     return []

    if 0 not in plot2text or plot2text[0] != 0:
        plot2text[0] = [0, ]

    for ploti in range(len(plot_chunks)):
        if ploti not in plot2text or not plot2text[ploti]:
            plot_text_pair[-1][0].append(ploti)
        else:
            textl = plot2text[ploti][0]
            if ploti > 0:
                if plot_text_pair[-1][1][0] == textl:
                    plot_text_pair[-1][0].append(ploti)
                    continue
                elif plot_text_pair[-1][1][0] > textl:
                    plot_text_pair[-1][0].append(ploti)
                    continue
                else:
                    plot_text_pair[-1][1].extend(range(plot_text_pair[-1][1][0] + 1, textl))
            plot_text_pair.append(([ploti, ], [textl, ]))
    
    plot_text_pair[-1][1].extend(range(plot_text_pair[-1][1][0] + 1, len(text_chunks)))

    return plot_text_pair


