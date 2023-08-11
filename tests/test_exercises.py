from accounts.types import ChapterInfo, PillarInfo


def test_exercises_kind():
    assert ChapterInfo({'kind': 'Exercise'}).is_exercise()
    assert ChapterInfo({'kind': 'Problem'}).is_exercise()

    assert not ChapterInfo({'kind': 'Text'}).is_exercise()
    assert not ChapterInfo({'kind': 'Title'}).is_exercise()

def test_num_exercises():
    pillar = PillarInfo({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}, {'kind': 'Problem'}, {'kind': 'Title'}]})
    assert pillar.num_exercises == 2

    pillar = PillarInfo({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}], 'exercises': {1: 1, 2: 2}})
    assert pillar.num_exercises == 1 #ignore 'exercises'

    pillar = PillarInfo({'pillar_id': 1, 'chapter': [{'kind': 'Exercise'}] * 2, 'exercises': {1: 1}})
    assert pillar.num_exercises == 2 #ignore 'exercises'
