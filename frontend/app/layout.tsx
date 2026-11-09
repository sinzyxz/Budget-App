import type { Metadata } from "next";
import { IBM_Plex_Sans_Thai } from "next/font/google";
import "./globals.css";

const font = IBM_Plex_Sans_Thai({ subsets: ["thai", "latin"], weight: ["400", "500", "700"] });

export const metadata: Metadata = { title: "แบ่งเงินเดือน", description: "บันทึกรายรับรายจ่ายและแบ่งเงินตามสูตร" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="th">
      <body className={font.className}>{children}</body>
    </html>
  );
}
