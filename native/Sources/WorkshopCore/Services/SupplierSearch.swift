import Foundation

// MARK: – Result model

public struct SupplierSearchResult: Identifiable, Sendable {
    public let id: String               // "{slug}-{productId}-{variantId}"
    public let supplierSlug: String
    public let supplierName: String
    public let sku: String
    public let title: String
    public let price: Double            // unit price, USD
    public let currency: String
    public let inStock: Bool
    public let stockQty: Int?
    public let url: URL?

    public var priceString: String {
        String(format: "$%.2f", price)
    }
}

// MARK: – Shopify adapter
// Works for any Shopify storefront via the public /products.json endpoint.

public actor ShopifySearcher: Sendable {
    public let slug: String
    public let name: String
    private let baseURL: String
    private let session = URLSession.shared

    public init(slug: String, name: String, baseURL: String) {
        self.slug    = slug
        self.name    = name
        self.baseURL = baseURL
    }

    public func search(query: String) async throws -> [SupplierSearchResult] {
        guard let encoded = query.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed),
              let url = URL(string: "\(baseURL)/products.json?q=\(encoded)&limit=8") else {
            return []
        }

        let (data, response) = try await session.data(from: url)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { return [] }

        let decoded = try JSONDecoder().decode(ShopifyProductsResponse.self, from: data)

        return decoded.products.flatMap { product in
            product.variants.prefix(1).compactMap { variant -> SupplierSearchResult? in
                guard let priceVal = Double(variant.price) else { return nil }
                let handle = product.handle
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
                    url:          URL(string: "\(baseURL)/products/\(handle)")
                )
            }
        }
    }
}

// MARK: – Mouser adapter

public actor MouserSearcher: Sendable {
    private let session = URLSession.shared

    public init() {}

    public func search(query: String, apiKey: String) async throws -> [SupplierSearchResult] {
        guard !apiKey.isEmpty,
              let url = URL(string: "https://api.mouser.com/api/v1/search/keyword?apiKey=\(apiKey)") else {
            return []
        }

        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue("application/json", forHTTPHeaderField: "Accept")

        let body: [String: Any] = [
            "SearchByKeywordRequest": [
                "keyword": query,
                "records": 8,
                "startingRecord": 0,
                "searchOptions": "string",
                "searchWithYourSignUpLanguage": "false"
            ]
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await session.data(for: req)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { return [] }

        guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              let results = json["SearchResults"] as? [String: Any],
              let parts = results["Parts"] as? [[String: Any]] else { return [] }

        return parts.compactMap { part -> SupplierSearchResult? in
            guard let mfgPN = part["ManufacturerPartNumber"] as? String,
                  let mouserPN = part["MouserPartNumber"] as? String else { return nil }

            let desc = part["Description"] as? String ?? mfgPN
            let avail = (part["AvailabilityInStock"] as? String).flatMap(Int.init) ?? 0
            let inStock = avail > 0

            // Find lowest single-unit price
            var price: Double = 0
            if let breaks = part["PriceBreaks"] as? [[String: Any]] {
                for pb in breaks {
                    if let qtyStr = pb["Quantity"] as? Int, qtyStr == 1,
                       let prStr = (pb["Price"] as? String)?.replacingOccurrences(of: "$", with: "") {
                        price = Double(prStr) ?? 0
                        break
                    }
                }
                // Fallback: first break
                if price == 0, let first = breaks.first,
                   let prStr = (first["Price"] as? String)?.replacingOccurrences(of: "$", with: "") {
                    price = Double(prStr) ?? 0
                }
            }

            let productURL = URL(string: "https://www.mouser.com/ProductDetail/\(mouserPN.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? "")")

            return SupplierSearchResult(
                id:           "mouser-\(mouserPN)",
                supplierSlug: "mouser",
                supplierName: "Mouser Electronics",
                sku:          mouserPN,
                title:        desc,
                price:        price,
                currency:     "USD",
                inStock:      inStock,
                stockQty:     avail,
                url:          productURL
            )
        }
    }
}

// MARK: – Aggregate searcher

public actor SupplierSearchService: Sendable {
    public static let shared = SupplierSearchService()

    // Pre-configured Shopify stores
    public let tayda   = ShopifySearcher(slug: "tayda",    name: "Tayda Electronics",   baseURL: "https://www.taydaelectronics.com")
    public let mammoth = ShopifySearcher(slug: "mammoth",  name: "Mammoth Electronics", baseURL: "https://www.mammothelectronics.com")
    public let lms     = ShopifySearcher(slug: "lms",      name: "Love My Switches",    baseURL: "https://lovemyswitches.com")
    public let mouser  = MouserSearcher()

    private init() {}

    /// Search all enabled suppliers in parallel. `mouserKey` may be empty (skips Mouser).
    public func searchAll(query: String, mouserKey: String) async -> [SupplierSearchResult] {
        async let taydaR   = (try? await tayda.search(query: query))   ?? []
        async let mammothR = (try? await mammoth.search(query: query)) ?? []
        async let lmsR     = (try? await lms.search(query: query))     ?? []
        async let mouserR  = mouserKey.isEmpty ? [] : ((try? await mouser.search(query: query, apiKey: mouserKey)) ?? [])

        let all = await taydaR + mammothR + lmsR + mouserR
        return all.sorted { $0.price < $1.price }
    }
}

// MARK: – Shopify JSON response models (private)

private struct ShopifyProductsResponse: Decodable {
    let products: [ShopifyProduct]
}

private struct ShopifyProduct: Decodable {
    let id: Int
    let title: String
    let handle: String
    let variants: [ShopifyVariant]
}

private struct ShopifyVariant: Decodable {
    let id: Int
    let sku: String?
    let price: String          // Shopify prices are strings: "0.09"
    let available: Bool
    let inventoryQuantity: Int?

    enum CodingKeys: String, CodingKey {
        case id, sku, price, available
        case inventoryQuantity = "inventory_quantity"
    }
}
