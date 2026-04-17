select
    review_id,
    order_id,
    review_score,
    review_comment
from {{ source('raw', 'reviews') }}
