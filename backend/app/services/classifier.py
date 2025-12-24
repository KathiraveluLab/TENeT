def classify_specialist(taxonomy: str) -> set[str]:
    categories = set()

    if not taxonomy:
        return {"physical"} 

    taxonomy = taxonomy.lower()
    if any(t in taxonomy for t in PHYSICAL_TAXONOMIES):
        categories.add("physical")

    if any(t in taxonomy for t in TELEHEALTH_TAXONOMIES):
        categories.add("telehealth")

    if any(t in taxonomy for t in EXCLUDED_TAXONOMIES) and not categories:
        return set()

    if not categories:
        categories.add("physical") 

    return categories
PHYSICAL_TAXONOMIES = {
    "emergency medicine",
    "surgery",
    "general acute care hospital",
    "urgent care",
    "ambulance",
    "air transport",
    "land transport",
    "water transport",
    "anesthesiology",
    "radiology",
    "diagnostic radiology",
    "pathology",
    "dialysis",
    "end-stage renal disease (esrd) treatment",
    "obstetrics",
    "gynecology",
    "obstetrics & gynecology",
    "orthopaedic surgery",
    "orthopaedic surgery of the spine",
    "neurological surgery",
    "urology",
    "ophthalmology",
    "otolaryngology",
    "oral and maxillofacial surgery",
    "physical therapy",
    "physical therapist",
    "physical therapy assistant",
    "rehabilitation",
    "inpatient",
    "skilled nursing facility",
    "long term care hospital",
    "respiratory therapist",
    "sleep disorder diagnostic",
}
TELEHEALTH_TAXONOMIES = {
    "psychiatry",
    "psychology",
    "mental health",
    "psychologist",
    "counselor",
    "social worker",
    "behavior analyst",
    "behavior technician",
    "addiction medicine",
    "addiction psychiatry",
    "substance use disorder",
    "family medicine",
    "internal medicine",
    "primary care",
    "endocrinology",
    "diabetes",
    "nutrition",
    "obesity and weight management",
    "pediatrics",
    "gerontology",
    "pain medicine",
    "sleep medicine",
}
EXCLUDED_TAXONOMIES = {
    "pharmacy",
    "pharmacist",
    "community/retail pharmacy",
    "pharmacy technician",
    "clinic pharmacy",
}