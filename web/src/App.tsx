import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./pages/Overview";
import CustomerRisk from "./pages/CustomerRisk";
import CustomerDetail from "./pages/CustomerDetail";
import ComingSoon from "./pages/ComingSoon";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="musteri-riski" element={<CustomerRisk />} />
        <Route path="musteri-riski/:id" element={<CustomerDetail />} />
        <Route path="kayip-tahmini" element={<ComingSoon title="Kayıp Tahmini" />} />
        <Route path="mudahale-planlari" element={<ComingSoon title="Müdahale Planları" />} />
        <Route path="model-ve-raporlar" element={<ComingSoon title="Model ve Raporlar" />} />
        <Route path="*" element={<ComingSoon title="Sayfa bulunamadı" />} />
      </Route>
    </Routes>
  );
}
