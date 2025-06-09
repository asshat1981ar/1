import { useState } from "react";

export default function CTAFormSection() {
  const [formData, setFormData] = useState({ name: "", email: "", honeypot: "" });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (formData.honeypot) return;
    alert("Submitted! We'll be in touch.");
  };

  return (
    <section id="cta" className="bg-red-600 text-white py-20 px-6">
      <div className="max-w-2xl mx-auto text-center">
        <h2 className="text-4xl font-bold mb-6">Let’s Talk Results</h2>
        <p className="mb-8 text-lg">
          Download our pitch deck or just book a call.
        </p>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <input
            type="text"
            name="name"
            placeholder="Your name"
            value={formData.name}
            onChange={handleChange}
            className="p-3 rounded-md text-black"
            required
          />
          <input
            type="email"
            name="email"
            placeholder="Your email"
            value={formData.email}
            onChange={handleChange}
            className="p-3 rounded-md text-black"
            required
          />
          <input
            type="text"
            name="honeypot"
            value={formData.honeypot}
            onChange={handleChange}
            className="hidden"
          />
          <button
            type="submit"
            className="bg-black hover:bg-gray-800 text-white py-3 px-6 rounded-full mt-2"
          >
            Book a Call →
          </button>
          <a
            href="/media/no-bull-deck.pdf"
            className="text-sm underline mt-2 text-white hover:text-gray-200"
            download
          >
            Download Our Deck
          </a>
        </form>
      </div>
    </section>
  );
}