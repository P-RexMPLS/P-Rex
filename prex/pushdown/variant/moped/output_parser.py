import re


_transition_text_regex = re.compile(r'\[\s*(?P<transition_text>\w+)\s*\]')


def read_trace(trace):
    transition_texts = []
    for line in trace:
        stripped = line.strip()
        match = _transition_text_regex.match(stripped)
        if match:
            transition_texts.append(match['transition_text'])

    return transition_texts


def map_trace(trace, transition_index):
    # Mapping is transition: transition_text
    # Invert because we have to go back!
    reverse_mapping = {value: key for key, value in transition_index.items()}
    transition_texts = read_trace(trace)
    transitions = [reverse_mapping[text] for text in transition_texts]

    return transitions


def parse_output(lines, transition_index):
    if 'YES' in lines[0]:
        result = True
    elif 'NO' in lines[0]:
        result = False
    else:
        raise RuntimeError('¿Qué')

    transitions = map_trace(lines, transition_index)

    return result, transitions
