import { useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import PageHeader from "../components/PageHeader";
import Button from "../components/Button";

/** Henüz tasarlanmamış sayfalar için yer tutucu */
export default function ComingSoon({ title }: { title: string }) {
  const navigate = useNavigate();
  return (
    <>
      <PageHeader title={title} />
      <main className="mx-auto flex max-w-7xl flex-col items-start gap-4 p-8">
        <div className="w-full rounded border border-line bg-surface p-10">
          <p className="text-sm font-semibold text-forest">Bu sayfa henüz hazır değil.</p>
          <p className="mt-1 text-xs text-ink-2">Genel Bakış sonrası sırayla tasarlanacak.</p>
          <Button variant="secondary" icon={ArrowLeft} onClick={() => navigate("/")} className="mt-5">
            Genel Bakış'a Dön
          </Button>
        </div>
      </main>
    </>
  );
}
