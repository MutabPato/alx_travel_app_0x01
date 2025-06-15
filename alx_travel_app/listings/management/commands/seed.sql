-- Insert listings
INSERT INTO listing (name, description, location, pricepernight)
VALUES
('Ocean Breeze', 'Beachside apartment', 'Diani', 4000.00),
('Mountain Escape', 'Cabin with scenic views', 'Naivasha', 3000.00),
('City Center Loft', 'Modern flat in CBD', 'Nairobi', 5000.00),
('Lush Garden Retreat', 'Quiet home with garden', 'Karen', 2500.00);

-- Insert bookings (listing_id must reference existing IDs from listing)
INSERT INTO booking (listing_id, start_date, end_date, total_price, status)
VALUES
(3, '2025-06-01', '2025-06-05', 16000.00, 'confirmed'),
(4, '2025-06-10', '2025-06-15', 15000.00, 'pending'),
(1, '2025-06-20', '2025-06-23', 15000.00, 'cancelled'),
(2, '2025-07-01', '2025-07-03', 6000.00, 'confirmed');

-- Insert reviews (listing_id must reference existing IDs from listing)
INSERT INTO review (listing_id, rating, comment)
VALUES
(3, 4, 'Amazing view and great stay'),
(4, 3, 'Nice place but a bit noisy'),
(1, 5, 'Super clean and modern'),
(2, 4, 'Perfect for a weekend getaway');
