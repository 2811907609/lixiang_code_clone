from dataclasses import dataclass

from sentence_transformers import SentenceTransformer
from inference_server.backend.common import register
from inference_server.backend.basemodel import BaseModel


@register('ST')
@dataclass
class ST(BaseModel):
    model: None

    @classmethod
    async def new_model(cls, model_path: str = '', **kwargs):
        model = SentenceTransformer(model_path)
        return cls(model=model)

    def embed(self, input, normalize_embeddings=True):
        tokens = self.model.encode(input,
                                   normalize_embeddings=normalize_embeddings)
        return tokens


@register('st_reranker')
@dataclass
class STReranker(BaseModel):
    model: None

    @classmethod
    async def new_model(cls, model_path: str = '', **kwargs):
        from sentence_transformers import CrossEncoder
        model = CrossEncoder(model_path)
        return cls(model=model)

    def predict_scores(self, query, inputs):
        '''the larger the score, the closer the relations'''
        inputs_ = [[query, input] for input in inputs]
        scores = self.model.predict(inputs_)
        return scores.tolist()
