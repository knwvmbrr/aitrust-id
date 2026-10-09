// Catalogue definitions are not evaluated answers; keep that distinction in saved files.
export function catalogueExport(tag, use, performance, scopeFeatures) {
  return {...tag, format:'ai-trust-id-catalogue/v1', record_type:'catalogue_description',
    evaluated_result:false, use, performance, scopeFeatures};
}
