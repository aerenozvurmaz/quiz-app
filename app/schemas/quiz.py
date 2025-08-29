from marshmallow import Schema, fields, validate

class OptionSchema(Schema):
    id = fields.Int(dump_only=True) #appear in output, ignored in input
    text = fields.Str(required=True)
    is_correct = fields.Bool(load_default=False)

class QuestionSchema(Schema):
    id = fields.Int(dump_only=True)
    order = fields.Int()
    text = fields.Str(required=True)
    points = fields.Int(load_default=None)
    category = fields.Str(required=True, validate=validate.OneOf(
        ["science", "history", "sport", "geography", "art"]
    ))
    difficulty = fields.Str(load_default="easy", validate = validate.OneOf(
        ["easy", "medium", "hard"]
    ))
    options = fields.List(fields.Nested(OptionSchema), required=True)

class QuizCreateSchema(Schema):
    title = fields.Str(required=True)
    week_start_date = fields.Date(required=True)
    opens_at = fields.DateTime(required=True)
    closes_at = fields.DateTime(required=True)
    questions = fields.List(fields.Nested(QuestionSchema), load_default = [])


class AnswerSchema(Schema):
    option_id = fields.Int(required=False, allow_none=True, load_default=None)

class QuizBriefSchema(Schema):
    id = fields.Int()
    week_start_date = fields.Date()
    opens_at = fields.DateTime()
    closes_at = fields.DateTime()
    published_at = fields.DateTime(allow_none=True)
    title = fields.Str()


class OptionPublicSchema(Schema):
    id = fields.Int(dump_only=True) #appear in output, ignored in input
    text = fields.Str(required=True)

class QuestionPublicSchema(Schema):
    id = fields.Int()
    order = fields.Int()
    text = fields.Str()
    category = fields.Str()
    options = fields.List(fields.Nested(OptionPublicSchema))

class QuestionPaperPublicSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    week_start_date = fields.Date()
    opens_at = fields.DateTime()
    closes_at = fields.DateTime()
    questions = fields.List(fields.Nested(QuestionPublicSchema))

class QuizPaperPublicSchema(Schema):
    id = fields.Int()
    title = fields.Str()
    week_start_date = fields.Date()
    opens_at = fields.DateTime()
    closes_at = fields.DateTime()
    questions = fields.List(fields.Nested(QuestionPublicSchema))