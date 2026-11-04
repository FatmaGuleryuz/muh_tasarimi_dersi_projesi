# Test Diff — kayip-musteri-postmortem (red)

Yeni dosya: `backend/tests/test_postmortem.py`. Yazan: backend-copilot (Haiku alt-ajanı). Testler henüz çalıştırılmadı.

| AC | Test | Sözleşme satırı |
|---|---|---|
| AC-1 | test_ac1_list_summary_matches_csv_recount | 1 |
| AC-2 | test_ac2_detail_schema_and_outcome_risk_consistency | 1b |
| AC-3 | test_ac3_outcome_filter_returns_only_matching_items[caught/partial/missed] | 1 |
| AC-4 | test_ac4_unknown_id_returns_404_with_exact_detail | 3 |
| AC-5 | test_ac5_existing_non_churned_id_returns_409_with_exact_detail | 3b |
| AC-6 | test_ac6_invalid_outcome_or_limit_returns_422[4] | 2 |
| AC-7 + AC-S2 | test_ac7_load_failure_returns_503_generic_body_and_logs[liste/detay] | 5 |
| AC-8 | test_ac8_no_lost_customers_returns_empty_items_and_zero_summary, test_ac8_empty_dataframe_returns_all_summary_values_zero | 8 |
| AC-9 | test_ac9_blank_total_charges_for_lost_customer_is_null | 7 |
| AC-10 | test_ac10_top_reason_missing_from_shap_gives_null_rank, test_ac10_known_feature_rank_is_position_in_shap_keys | 7 |
| AC-S1 | test_ac_s1_malicious_ids_return_404_without_other_customer_data[3] | 3 |
| AC-11/12 | UI — test altyapısı yok, kontrolü verify/vision-test'e bırakıldı | — |

Alt-ajanın notu: liste testleri `limit=1000` kullanıyor. Implementasyon da varsayılan limit ile
tüm kayıpları döndürmeli ya da test bunu açıkça istemeli.
