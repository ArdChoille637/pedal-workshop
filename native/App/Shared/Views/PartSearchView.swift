// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import SwiftUI
import WorkshopCore

/// Standalone supplier parts search (the sidebar "Price Lookup").
///
/// A free keyword search across the configured suppliers — Mammoth (no key
/// needed) and Mouser (when a Mouser API key is set in Settings). Unlike
/// `PriceLookupView`, which links a result to a specific inventory component,
/// this is for quickly looking up live prices and stock. To save a price
/// against a part, open a component in Inventory and use "Find Prices".
struct PartSearchView: View {
    @Environment(WorkshopStore.self) var store

    @State private var query = ""
    @State private var results: [SupplierSearchResult] = []
    @State private var isLoading = false
    @State private var searched = false
    @State private var hasMouserKey = false

    var body: some View {
        VStack(spacing: 0) {
            searchBar
            Divider()

            if !hasMouserKey { keyHint }

            if !store.supplierSearchNotices.isEmpty {
                Label(store.supplierSearchNotices.joined(separator: " · "),
                      systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .padding(.horizontal, 12)
                    .padding(.top, 6)
            }

            content
        }
        .navigationTitle("Price Lookup")
        .onAppear { hasMouserKey = !store.mouserAPIKey.isEmpty }
    }

    // MARK: – Search bar

    private var searchBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "magnifyingglass").foregroundStyle(.secondary)
            TextField("Search parts — e.g. “1N4148”, “100k resistor”, “TL072”…", text: $query)
                .textFieldStyle(.plain)
                .onSubmit { Task { await runSearch() } }
            if isLoading {
                ProgressView().scaleEffect(0.7)
            } else {
                Button("Search") { Task { await runSearch() } }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.small)
                    .disabled(query.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(12)
        .background(.background.secondary)
    }

    // MARK: – Mouser-key hint

    private var keyHint: some View {
        Label("Searching Mammoth only. Add a Mouser API key in Settings to include Mouser's catalog.",
              systemImage: "key")
            .font(.caption)
            .foregroundStyle(.secondary)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.yellow.opacity(0.08))
    }

    // MARK: – Content

    @ViewBuilder
    private var content: some View {
        if isLoading {
            ProgressView("Searching…")
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else if results.isEmpty {
            ContentUnavailableView {
                Label(searched ? "No results" : "Search for parts",
                      systemImage: searched ? "cart.badge.questionmark" : "magnifyingglass")
            } description: {
                Text(searched
                     ? "No matches from Mammoth\(hasMouserKey ? " or Mouser" : ""). Try a different term."
                     : "Look up live prices and stock from Mammoth\(hasMouserKey ? " and Mouser" : "").")
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            List(results) { result in
                // No per-component link in standalone search — onSave omitted.
                PriceResultRow(result: result, isSaved: false)
            }
            .listStyle(.inset)
        }
    }

    // MARK: – Actions

    private func runSearch() async {
        let q = query.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return }
        isLoading = true
        results = await store.searchSuppliers(query: q)
        isLoading = false
        searched = true
    }
}
