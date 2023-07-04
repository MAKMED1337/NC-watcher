from accounts.types import Pillar, Chapter

def test_exercises_kind():
    assert Chapter({'kind': 'Exercise'}).is_exercise()
    assert Chapter({'kind': 'Problem'}).is_exercise()

    assert not Chapter({'kind': 'Text'}).is_exercise()
    assert not Chapter({'kind': 'Title'}).is_exercise()

def test_num_exercises():
    pillar = Pillar({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}, {'kind': 'Problem'}, {'kind': 'Title'}]})
    assert pillar.num_exercises == 2

    pillar = Pillar({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}], 'exercises': {1: 1, 2: 2}})
    assert pillar.num_exercises == 1 #ignore 'exercises'

    pillar = Pillar({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}] * 2, 'exercises': {1: 1}})
    assert pillar.num_exercises == 2 #ignore 'exercises'