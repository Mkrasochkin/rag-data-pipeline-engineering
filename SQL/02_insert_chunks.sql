INSERT INTO public.chunks (
    qdrant_point_id,
    doc_id,
    section_id,
    workspace_id,
    section_path,
    clause_start,
    clause_end,
    clause_numbers,
    clause_display,
    merged_clauses_count,
    chunk_index,
    content_type,
    parent_chunk_id,
    content_url,
    text_content,
    token_count
)
SELECT
    %(qdrant_point_id)s,
    d.id,
    NULL, -- section_id - на данном этапе разработки NULL,
    d.workspace_id,
    %(section_path)s,
    %(clause_start)s,
    %(clause_end)s,
    %(clause_numbers)s,
    %(clause_display)s,
    %(merged_clauses_count)s,
    %(chunk_index)s,
    %(content_type)s,
    %(parent_chunk_id)s, -- на данном этапе разработки NULL,
    %(content_url)s,
    %(text_content)s,
    %(token_count)s
FROM public.documents AS d
WHERE 
    d.designation = %(designation)s AND
    d.year = %(year)s AND
    d.type = %(type)s;