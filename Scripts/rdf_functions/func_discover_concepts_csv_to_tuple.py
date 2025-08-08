def discover_concepts_csv_to_tuple(input_csv_path: str,
                      broader_terms: list[str],
                      narrower_terms: list[str],
                      related_terms: list[str],
                      non_preferred_terms: list[str],
                      subject_categories: list[str]) -> tuple[set, set, set]:
    """
    Performs the first pass on the CSV to identify all concepts, non-preferred terms,
    and subject categories based on configurable relationship types.
    
    Args:
        input_csv_path (str): Path to the input CSV file.
        broader_terms (list[str]): Predicates for broader relationships.
        narrower_terms (list[str]): Predicates for narrower relationships.
        related_terms (list[str]): Predicates for related relationships.
        non_preferred_terms (list[str]): Predicates for non-preferred terms.
        subject_categories (list[str]): Predicates for subject categories.
    
    Returns:
        tuple[set, set, set]: A tuple containing the set of concept terms,
                              non-preferred terms, and subject categories.
    """
    concept_terms = set()
    non_preferred_set = set()
    subject_categories_set = set()
    
    with open(input_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) == 3:
                subject_raw, predicate_raw, obj_raw = row
                
                subject_term = clean_term(subject_raw)
                object_term = clean_term(obj_raw)
                
                concept_terms.add(subject_term)
                
                if predicate_raw in broader_terms + narrower_terms + related_terms + subject_categories:
                    concept_terms.add(object_term)
                
                if predicate_raw in non_preferred_terms:
                    non_preferred_set.add(subject_term)
                
                if predicate_raw in subject_categories:
                    subject_categories_set.add(object_term)
                    
    concept_terms -= non_preferred_set
    return concept_terms, non_preferred_set, subject_categories_set