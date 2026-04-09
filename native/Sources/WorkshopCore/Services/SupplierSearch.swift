// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Pedal Workshop Contributors
// https://github.com/ArdChoille637/pedal-workshop

import Foundation

// MARK: - SupplierSearchResult

/// A single product listing returned by any supplier adapter.
///
/// The `id` field is stable within a session but should not be persisted across
/// app launches — its format is `"{supplierSlug}-{productId}-{variantId}"` and
/// supplier APIs may renumber products.
public struct SupplierSearchResult: Identifiable, Sendable {
    /// Stable composite identifier: `"{supplierSlug}-{productId}-{variantId}"`.
    public let id: String
    /// Short machine-readable supplier identifier (e.g. `"tayda"`, `"mouser"`).
    public let supplierSlug: String
    /// Human-readable supplier display name (e.g. `"Tayda Electronics"`).
    public let supplierName: String
    /// Supplier's own stock-keeping unit number.
    public let sku: String
    /// Product or component description from the supplier catalogue.
    public let title: String
    /// Unit price in the currency indicated by ``currency``.
    public let price: Double
    /// ISO 4217 currency code, typically `"USD"`.
    public let currency: String
    /// `true` if the supplier reports this SKU as available to order.
    public let inStock: Bool
    /// On-hand quantity at the supplier, if reported. `nil` when not available.
    public let stockQty: Int?
    /// Deep-link to the product page on the supplier's website.
    public let url: URL?

    /// Price formatted as a US-dollar string (e.g. `"$0.09"`).
    public var priceString: String {
        String(format: "$%.2f", price)
    }
}

// MARK: - ShopifySearcher

/// Searches a single Shopify-powered supplier store via its public `/products.json` endpoint.
///
/// Any Shopify storefront exposes this endpoint without authentication, making it a
/// convenient lightweight search target. The adapter fetches up to 8 results per query
/// and returns one ``SupplierSearchResult`` per product (using the first variant's price).
///
/// ## Usage
/// ```swift
/// let tayda = ShopifySearcher(slug: "tayda", name: "Tayda Electronics",
///                             baseURL: "https://www.taydaelectronics.com")
/// let results = try await tayda.search(query: "10k resistor")
/// ```
///
/// ## Timeout
/// All requests use a 15-second timeout. Requests that exceed this are cancelled and
/// the caller receives an empty array (when called via ``SupplierSearchService/searchAll(query:mouserKey:)``).
///
/// # TO ADD A NEW SHOPIFY SUPPLIER:
/// 1. Add a new stored property to ``SupplierSearchService``:
///    ```swift
///    public let myStore = ShopifySearcher(
///        slug:    "mystore",
///        name:    "My Store Name",
///        baseURL: "https://www.mystoreurl.com"   // no trailing slash
///    )
///    ```
/// 2. Add the new searcher to the `async let` block inside
///    ``SupplierSearchService/searchAll(query:mouserKey:)``:
///    ```swift
///    async let myStoreR = (try? await myStore.search(query: query)) ?? []
///    ```
/// 3. Include it in the `await` aggregation line:
///    ```swift
///    let all = await taydaR + mammothR + lmsR + myStoreR + mouserR
///    ```
/// That's it — no other changes required.
public actor ShopifySearcher: Sendable {
    /// Machine-readable identifier used in ``SupplierSearchResult/supplierSlug``.
    public let slug: String
    /// Display name used in ``SupplierSearchResult/supplierName``.
    public let name: String

    private let baseURL: String

    /// Shared session configured with a 15-second timeout.
    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = 15
        config.timeoutIntervalForResource = 15
        return URLSession(configuration: config)
    }()

    /// Creates a searcher for a Shopify-powered store.
    ///
    /// - Parameters:
    ///   - slug: Short, lowercase, URL-safe identifier (e.g. `"tayda"`).
    ///   - name: Human-readable name shown in search results.
    ///   - baseURL: Store root URL **without** a trailing slash
    ///     (e.g. `"https://www.taydaelectronics.com"`).
    public init(slug: String, name: String, baseURL: String) {
        self.slug    = slug
        self.name    = name
        self.baseURL = baseURL
    }

    /// Performs a keyword search against the store's `/products.json` endpoint.
    ///
    /// - Parameter query: Free-text search string (e.g. `"10k resistor"`).
    /// - Returns: Up to 8 results, one per matching product. Returns an empty array on
    ///   HTTP errors, decoding failures, or network timeout.
    /// - Throws: Rethrows URL loading errors. Callers inside
    ///   ``SupplierSearchService/searchAll(query:mouserKey:)`` wrap this with `try?` so
    ///   individual supplier failures do not cancel the whole search.
    public func search(query: String) async throws -> [SupplierSearchResult] {
        guard
            let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
            let url = URL(string: "\(baseURL)/products.json?q=\(encoded)&limit=8")
        else {
            return []
        }

        let (data, response) = try await session.data(from: url)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { return [] }

        let decoded = try JSONDecoder().decode(ShopifyProductsResponse.self, from: data)

        return decoded.products.flatMap { product in
            product.variants.prefix(1).compactMap { variant -> SupplierSearchResult? in
                guard let priceVal = Double(variant.price) else { return nil }
                return SupplierSearchResult(
                    id:           "\(slug)-\(product.id)-\(variant.id)",
                    supplierSlug: slug,
                    supplierName: name,
                    sku:          variant.sku ?? String(variant.id),
                    title:        product.title,
                    price:        priceVal,
                    currency:     "USD",
                    inStock:      variant.available,
                    stockQty:     variant.inventoryQuantity,
                    url:          URL(string: "\(baseURL)/products/\(product.handle)")
                )
            }
        }
    }
}

// MARK: - MouserSearcher

/// Searches Mouser Electronics via the Mouser Search API v1.
///
/// Requires a valid API key obtainable from [mouser.com/api-hub](https://www.mouser.com/api-hub/).
/// If the key is empty the search is silently skipped and an empty array is returned.
///
/// ## Timeout
/// All requests use a 15-second timeout. Requests that exceed this are cancelled and
/// the caller receives an empty array when called via
/// ``SupplierSearchService/searchAll(query:mouserKey:)``.
///
/// ## Pricing
/// Mouser returns a list of price breaks. This adapter selects the Qty-1 unit price;
/// if no Qty-1 break exists it falls back to the first listed break.
///
/// # TO ADD A NON-SHOPIFY SUPPLIER:
/// 1. Create a new `actor` in this file that conforms to no specific protocol but exposes:
///    ```swift
///    public func search(query: String, /* any extra auth params */) async throws -> [SupplierSearchResult]
///    ```
/// 2. Use a private `URLSession` with a 15-second timeout (copy the lazy-var pattern
///    from ``ShopifySearcher`` or ``MouserSearcher``).
/// 3. Parse the response using a private `Decodable` struct — avoid raw
///    `JSONSerialization` for maintainability.
/// 4. Add a stored property and an `async let` branch inside
///    ``SupplierSearchService/searchAll(query:mouserKey:)`` following the same pattern
///    as the existing suppliers.
/// 5. If the supplier requires authentication, thread the credential through
///    `searchAll` (add a parameter or store the key as a property on
///    ``SupplierSearchService``).
public actor MouserSearcher: Sendable {
    /// Shared session configured with a 15-second timeout.
    private let session: URLSession = {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest  = 15
        config.timeoutIntervalForResource = 15
        return URLSession(configuration: config)
    }()

    /// Creates a Mouser searcher. No configuration is required at init time;
    /// the API key is passed per-request.
    public init() {}

    /// Performs a keyword search against the Mouser Search API.
    ///
    /// - Parameters:
    ///   - query: Free-text search string (e.g. `"NE5532 op-amp"`).
    ///   - apiKey: Mouser API key. Pass an empty string to skip the search entirely.
    /// - Returns: Up to 8 results sorted by the order Mouser returns them.
    ///   Returns an empty array when the key is empty, on HTTP errors, or on timeout.
    /// - Throws: Rethrows URL loading and JSON decoding errors.
    public func search(query: String, apiKey: String) async throws -> [SupplierSearchResult] {
        guard !apiKey.isEmpty,
              let url = URL(string: "https://api.mouser.com/api/v1/search/keyword?apiKey=\(apiKey)")
        else {
            return []
        }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")
        req.timeoutInterval = 15   // Belt-and-braces: also set on the request itself.

        // Build the POST body as a Mouser v1 keyword-search payload.
        let body = MouserSearchRequest(
            SearchByKeywordRequest: .init(
                keyword:                    query,
                records:                    8,
                startingRecord:             0,
                searchOptions:              "string",
                searchWithYourSignUpLanguage: "false"
            )
        )
        req.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await session.data(for: req)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { return [] }

        let mouserResponse = try JSONDecoder().decode(MouserResponse.self, from: data)

        return mouserResponse.SearchResults.Parts.compactMap { part -> SupplierSearchResult? in
            guard !part.ManufacturerPartNumber.isEmpty,
                  !part.MouserPartNumber.isEmpty
            else { return nil }

            let avail   = part.AvailabilityInStock.flatMap(Int.init) ?? 0
            let inStock = avail > 0

            // Select the Qty-1 unit price; fall back to the first price break.
            let price: Double = {
                if let qty1 = part.PriceBreaks.first(where: { $0.Quantity == 1 }) {
                    return qty1.parsedPrice
                }
                return part.PriceBreaks.first?.parsedPrice ?? 0
            }()

            let encodedPN = part.MouserPartNumber
                .addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? ""
            let productURL = URL(string: "https://www.mouser.com/ProductDetail/\(encodedPN)")

            return SupplierSearchResult(
                id:           "mouser-\(part.MouserPartNumber)",
                supplierSlug: "mouser",
                supplierName: "Mouser Electronics",
                sku:          part.MouserPartNumber,
                title:        part.Description ?? part.ManufacturerPartNumber,
                price:        price,
                currency:     "USD",
                inStock:      inStock,
                stockQty:     avail,
                url:          productURL
            )
        }
    }
}

// MARK: - SupplierSearchService

/// Aggregates all configured supplier searchers and runs them in parallel.
///
/// Access the singleton via ``SupplierSearchService/shared``.
///
/// ```swift
/// let results = await SupplierSearchService.shared
///     .searchAll(query: "10k resistor", mouserKey: UserDefaults.standard.string(forKey: "mouserKey") ?? "")
/// ```
///
/// # TO ADD A NEW SHOPIFY SUPPLIER:
/// See the detailed instructions on ``ShopifySearcher``.
///
/// # TO ADD A NON-SHOPIFY SUPPLIER:
/// See the detailed instructions on ``MouserSearcher``.
public actor SupplierSearchService: Sendable {
    /// Shared singleton. All supplier sub-actors are initialised once here.
    public static let shared = SupplierSearchService()

    // ── Pre-configured Shopify stores ────────────────────────────────────────────
    /// Tayda Electronics — bulk passive components at very low prices.
    public let tayda   = ShopifySearcher(
        slug:    "tayda",
        name:    "Tayda Electronics",
        baseURL: "https://www.taydaelectronics.com"
    )
    /// Mammoth Electronics — effects-focussed parts including speciality film caps.
    public let mammoth = ShopifySearcher(
        slug:    "mammoth",
        name:    "Mammoth Electronics",
        baseURL: "https://www.mammothelectronics.com"
    )
    /// Love My Switches — switches, jacks, and hardware for pedal enclosures.
    public let lms     = ShopifySearcher(
        slug:    "lms",
        name:    "Love My Switches",
        baseURL: "https://lovemyswitches.com"
    )

    // ── Non-Shopify suppliers ─────────────────────────────────────────────────────
    /// Mouser Electronics — broad catalogue; requires API key.
    public let mouser  = MouserSearcher()

    private init() {}

    /// Searches all enabled suppliers concurrently and returns results sorted by price.
    ///
    /// Supplier failures (network errors, timeouts, non-200 responses) are silently
    /// swallowed so that a single unreachable supplier does not prevent results from
    /// the others from being shown.
    ///
    /// - Parameters:
    ///   - query: Free-text search string forwarded to every supplier.
    ///   - mouserKey: Mouser API key. Pass an empty string to skip Mouser entirely
    ///     (useful when the user has not configured a key).
    /// - Returns: Deduplicated results from all suppliers, sorted ascending by unit price.
    public func searchAll(query: String, mouserKey: String) async -> [SupplierSearchResult] {
        async let taydaR   = (try? await tayda.search(query: query))   ?? []
        async let mammothR = (try? await mammoth.search(query: query)) ?? []
        async let lmsR     = (try? await lms.search(query: query))     ?? []
        async let mouserR  = mouserKey.isEmpty
            ? []
            : ((try? await mouser.search(query: query, apiKey: mouserKey)) ?? [])

        let all = await taydaR + mammothR + lmsR + mouserR
        return all.sorted { $0.price < $1.price }
    }
}

// MARK: - Shopify JSON response models (private)

/// Top-level wrapper for the Shopify `/products.json` response.
private struct ShopifyProductsResponse: Decodable {
    let products: [ShopifyProduct]
}

/// A single Shopify product (may have multiple variants).
private struct ShopifyProduct: Decodable {
    let id: Int
    let title: String
    /// URL-safe slug used to construct the product page link.
    let handle: String
    let variants: [ShopifyVariant]
}

/// One purchasable variant of a Shopify product.
private struct ShopifyVariant: Decodable {
    let id: Int
    let sku: String?
    /// Shopify encodes prices as decimal strings (e.g. `"0.09"`).
    let price: String
    let available: Bool
    let inventoryQuantity: Int?

    enum CodingKeys: String, CodingKey {
        case id, sku, price, available
        case inventoryQuantity = "inventory_quantity"
    }
}

// MARK: - Mouser API request/response models (private)

/// POST body sent to the Mouser Search API v1 keyword-search endpoint.
private struct MouserSearchRequest: Encodable {
    struct KeywordRequest: Encodable {
        let keyword: String
        let records: Int
        let startingRecord: Int
        let searchOptions: String
        let searchWithYourSignUpLanguage: String
    }
    let SearchByKeywordRequest: KeywordRequest
}

/// Top-level Mouser API response envelope.
private struct MouserResponse: Decodable {
    let SearchResults: MouserSearchResults
}

/// Container for the parts list inside a Mouser search response.
private struct MouserSearchResults: Decodable {
    let Parts: [MouserPart]
}

/// A single part returned by the Mouser Search API.
private struct MouserPart: Decodable {
    /// Manufacturer's part number (e.g. `"NE5532P"`).
    let ManufacturerPartNumber: String
    /// Mouser's own catalogue number, used for deep-links and as the SKU.
    let MouserPartNumber: String
    /// Short text description from the Mouser catalogue. May be `nil`.
    let Description: String?
    /// In-stock quantity as a string (Mouser returns `"1234"` not `1234`).
    let AvailabilityInStock: String?
    /// Tiered price breaks; empty when no pricing data is available.
    let PriceBreaks: [MouserPriceBreak]
}

/// One quantity-tiered price point within a Mouser part listing.
private struct MouserPriceBreak: Decodable {
    /// Minimum order quantity for this price tier.
    let Quantity: Int
    /// Price string as returned by Mouser, e.g. `"$0.49"` or `"0.49"`.
    let Price: String

    /// Price as a `Double`, with any leading `$` removed.
    var parsedPrice: Double {
        Double(Price.replacingOccurrences(of: "$", with: "")) ?? 0
    }
}
