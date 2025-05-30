import os

import time
import os



class OpenAIGen:

    def __init__(self, model):

        self.model = model

    def gen(self, messages, temperature=0, seed=True, top_k=1):
        '''
        messages: [{'role': 'system', 'content': 'You are an intelligent code assistant'},
                   {'role': 'user', 'content': 'Translate this program...'},
                   {'role': 'assistant', 'content': 'Here is the translation...'},
                   {'role': 'user', 'content': 'Do something else...'}]
                   
        <returned>: ['Sure, here is...',
                     'Okay, let me see...',
                     ...]
        len(<returned>) == top_k
        '''
        # This is a dummy implementation for demonstration purposes.
        from .. import ModelException

        if top_k != 1 and temperature == 0:
            raise ModelException("Top k sampling requires a non-zero temperature")

        responses = []
        for _ in range(top_k):
            response = """
<FUNC>
// Hello World
</FUNC>
<WRAPPER>
// Hello World
</WRAPPER>"""
            responses.append(response.strip())

        return responses
